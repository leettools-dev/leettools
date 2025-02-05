import threading
import time
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from queue import Queue
from typing import Dict, List, Optional, Union

import leettools.common.exceptions as exceptions
from leettools.common.logging import get_logger
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler._impl.task_runner_eds import TaskRunnerEDS
from leettools.eds.scheduler._impl.task_scanner_kb import TaskScannerKB
from leettools.eds.scheduler.scheduler import AbstractScheduler
from leettools.eds.scheduler.schemas.job import Job, JobCreate
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.eds.scheduler.schemas.scheduler_status import SchedulerStatus
from leettools.eds.scheduler.schemas.task import Task, TaskStatus


class SchedulerSimple(AbstractScheduler):
    def __init__(
        self,
        context: Context,
        num_of_workers: int = 4,
    ):
        self.logger = get_logger(name="scheduler")
        self.logger.info("Initializing the simple scheduler.")

        self.context = context

        self.task_manager = context.get_task_manager()
        self.taskstore = self.task_manager.get_taskstore()
        self.jobstore = self.task_manager.get_jobstore()

        self.task_scanner = TaskScannerKB(context)
        self.target_org = None
        self.target_kb = None
        self.target_docsources = None

        self.task_runner = TaskRunnerEDS(context, self.logger)

        self.lock = threading.Lock()

        # todo: the operations of all these lists are connected, should be atomic
        self.task_queue: Queue[Union[Job, None]] = Queue()
        self.cooldown_queue: Queue[Union[Job, None]] = Queue()

        # the key is the task_uuid, the value is the job
        # we use these 4 dictionaries to keep track of the tasks
        self.tasks_running: Dict[str, Job] = {}
        self.tasks_in_cooldown_queue: Dict[str, Job] = {}
        self.tasks_in_queue: Dict[str, Job] = {}
        self.tasks_todo: Dict[str, JobStatus] = {}

        self.workers: Dict[int, Future] = {}
        self.task_loader: Union[Future, None] = None
        self.num_of_workers: int = num_of_workers
        self.threadpool: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=num_of_workers + 1
        )
        self.status: SchedulerStatus = SchedulerStatus.PAUSED
        self.logger.info("Finished initializing the simple scheduler.")

    def _current_task_info(self) -> str:
        return f"running/cd/queue/todo: {len(self.tasks_running)}/{len(self.tasks_in_cooldown_queue)}/{len(self.tasks_in_queue)}/{len(self.tasks_todo)}"

    def _clear_tasks(self) -> None:
        self.logger.info("Clearing tasks in the queue.")
        assert (
            self.status != SchedulerStatus.RUNNING
        ), f"Scheduler status is {self.status} while trying to clear tasks."
        with self.lock:
            self.logger.noop("Inside the lock ...", noop_lvl=3)
            if self.task_queue.qsize() > 0:
                while self.task_queue.qsize() > 0:
                    item = self.task_queue.get()
                    self.logger.info(f"Task queue has {item}, removing it.")
                    self.task_queue.task_done()

            if self.cooldown_queue.qsize() > 0:
                while self.cooldown_queue.qsize() > 0:
                    item = self.cooldown_queue.get()
                    self.logger.info(f"Paused queue has {item}, removing it.")
                    self.cooldown_queue.task_done()

            self.tasks_in_queue = {}
            self.tasks_in_cooldown_queue = {}
            self.tasks_running = {}
            self.tasks_todo = {}

            self.logger.info("Cleared tasks in the queue.")
        self.logger.noop("Outside the lock ...", noop_lvl=3)

    def _create_job_for_task_if_needed(self, task: Task) -> Optional[Job]:
        """
        This function is used when the scheduler found an incomplete task that is not
        in the queue.

        It checks the last job status for the task and create a new job if needed, also
        update the task status if needed.
        """
        job = None

        if task.task_status == TaskStatus.ABORTED:
            raise exceptions.UnexpectedCaseException(
                "Trying to create job for an aborted task."
            )
        if task.is_deleted:
            raise exceptions.UnexpectedCaseException(
                "Trying to create job for a deleted task."
            )

        task_uuid = task.task_uuid
        existing_job = self.jobstore.get_the_latest_job_for_task(task_uuid)
        if existing_job is None:
            self.logger.info(f"Found new task {task_uuid}. Creating new job for it.")
            job_create = JobCreate(task_uuid=task_uuid, program_spec=task.program_spec)
            job = self.jobstore.create_job(job_create)
        else:
            if existing_job.job_status == JobStatus.COMPLETED:
                self.logger.info(
                    f"Found complete job {existing_job.job_uuid} for task {task_uuid}."
                    "Mark task as completed."
                )
                self.taskstore.update_task_status(task_uuid, TaskStatus.COMPLETED)
                return None
            else:
                self.logger.info(
                    f"Found incomplete job {existing_job.job_uuid} for task {task_uuid}. "
                    "Mark the job as aborted and will create a new job."
                )
                self.jobstore.update_job_status(
                    existing_job.job_uuid, JobStatus.ABORTED
                )

                job_create = JobCreate(
                    task_uuid=task_uuid, program_spec=task.program_spec
                )
                job = self.jobstore.create_job(job_create)
        return job

    def _init_load_tasks(self) -> None:
        """
        This function is called when the scheduler is started or resumed.
        """
        assert (
            self.status != SchedulerStatus.RUNNING
        ), f"Scheduler status is {self.status} while trying to reload tasks."
        with self.lock:
            self.logger.noop("Inside the lock ...", noop_lvl=3)
            todo_tasks = self.task_scanner.scan_kb_for_tasks(
                target_org=self.target_org,
                target_kb=self.target_kb,
                target_docsources=self.target_docsources,
            )

            for task in todo_tasks:
                # deleted tasks won't be retrieved
                if task.is_deleted:
                    raise exceptions.UnexpectedCaseException(
                        "get_incomplete_tasks returned a deleted task."
                    )

                if task.task_status == TaskStatus.ABORTED:
                    self.logger.debug(
                        f"Found aborted task {task.task_uuid}. Skip it for now."
                    )
                    continue

                job = self._create_job_for_task_if_needed(task)
                if job == None:
                    continue
                self.tasks_todo[task.task_uuid] = job.job_status
                self.tasks_in_queue[task.task_uuid] = job
                self.taskstore.update_task_status(task.task_uuid, TaskStatus.PENDING)

            self.logger.info(
                f"Found {len(self.tasks_in_queue)} tasks, adding them to task queue."
            )
            for job in self.tasks_in_queue.values():
                self.logger.info(f"Adding job {job.job_uuid} to the queue.")
                self.task_queue.put(job)
        self.logger.noop("Outside the lock ...", noop_lvl=3)

    def _update_tasks(self) -> None:
        """
        This function is called with a specified interval to update the tasks.
        Logging inside this function should be very careful.
        """
        assert (
            self.status == SchedulerStatus.RUNNING
        ), f"Scheduler status is {self.status} while trying to load tasks."

        with self.lock:
            self.logger.noop("Inside the lock ...", noop_lvl=3)
            self.logger.noop("Scan the KB for new tasks ...", noop_lvl=1)
            todo_tasks = self.task_scanner.scan_kb_for_tasks(
                target_org=self.target_org,
                target_kb=self.target_kb,
                target_docsources=self.target_docsources,
            )

            self.logger.noop("Checking incomplete tasks ...", noop_lvl=1)
            for task in todo_tasks:
                if task.task_uuid in self.tasks_todo:
                    continue

                if task.is_deleted:
                    continue

                if task.task_status == TaskStatus.ABORTED:
                    self.logger.debug(f"Found aborted task {task.task_uuid}.")
                    continue

                self.logger.debug(f"Found incomplete task {task.task_uuid} ...")

                job = self._create_job_for_task_if_needed(task)
                if job == None:
                    continue

                self.tasks_in_queue[task.task_uuid] = job
                self.tasks_todo[task.task_uuid] = job.job_status
                self.task_queue.put(job)

        self.logger.noop("Outside the lock ...", noop_lvl=3)
        self._check_cooldown_queue()

    def _task_loader(self, interval: int) -> None:
        """
        The program executed in the task loader thread.
        """
        self.logger.info(
            f"Starting the task loader thread with interval {interval} seconds."
        )
        assert (
            self.status == SchedulerStatus.RUNNING
        ), f"Scheduler status is {self.status} while trying to load tasks."
        # we only print out log once every 1 minute
        logging_count = int(60 / interval)
        while self.status == SchedulerStatus.RUNNING:
            try:
                if logging_count == int(60 / interval):
                    self.logger.info(
                        f"Scanning data storage for new tasks. [{self._current_task_info()}]"
                    )
                    logging_count = logging_count - 1
                elif logging_count == 0:
                    logging_count = int(60 / interval)
                else:
                    logging_count = logging_count - 1

                self._update_tasks()
                time.sleep(interval)
            except Exception as e:
                tb_str = traceback.format_exc()
                self.logger.error(f"Error in the task loader: {tb_str}")
                raise e

        self.logger.info(f"The task loader thread is finished.")

    def _check_cooldown_queue(self) -> None:
        base_delay = self.context.settings.scheduler_base_delay_in_seconds
        max_retries = self.context.settings.scheduler_max_retries
        max_delay = self.context.settings.scheduler_max_delay_in_seconds
        if self.cooldown_queue.qsize() == 0:
            return

        self.logger.info(
            f"There are {self.cooldown_queue.qsize()} jobs in cooldown queue."
        )
        job = self.cooldown_queue.get()
        assert (
            job.job_status == JobStatus.FAILED
        ), f"Checking the delay time for a failed task {job.task_uuid}."
        if job.retry_count > max_retries:
            self.logger.warning(
                f"Job {job.job_uuid} has reached the max retry count {max_retries}."
            )
            job.job_status = JobStatus.ABORTED
            with self.lock:
                self.logger.noop("Inside the lock ...", noop_lvl=3)
                self.tasks_todo[job.task_uuid] = job.job_status
                self.tasks_in_cooldown_queue.pop(job.task_uuid)
            self.logger.noop("Outside the lock ...", noop_lvl=3)
        else:
            delay_in_seconds = min(max_delay, base_delay * 2**job.retry_count)
            diff: timedelta = time_utils.current_datetime() - job.last_failed_at
            if diff.total_seconds() < delay_in_seconds:
                # silently put the job back to the cooldown queue
                self.cooldown_queue.put(job)
            else:
                job.job_status = JobStatus.PENDING
                with self.lock:
                    self.logger.noop("Inside the lock ...", noop_lvl=3)
                    self.tasks_in_queue[job.task_uuid] = job
                    self.tasks_todo[job.task_uuid] = job.job_status
                    self.task_queue.put(job)
                    self.tasks_in_cooldown_queue.pop(job.task_uuid)
                self.logger.noop("Outside the lock ...", noop_lvl=3)
        self.taskstore.update_task_status(job.task_uuid, job.job_status)
        self.cooldown_queue.task_done()

    def _worker_executes_job(self, id: int, job: Job) -> None:
        try:
            updated_job = self.task_runner.run_job(job)
            if updated_job is not None:
                self.logger.info(
                    f"[{id}]Finished exeuting task {job.task_uuid} in the worker."
                    f"The job status is {updated_job.job_status}. "
                    f"(job_uuid {job.job_uuid})"
                )
                job.job_status = updated_job.job_status
            else:
                self.logger.error(
                    f"[{id}]The executor returns a null object for {job.task_uuid}."
                    f"(job_uuid {job.job_uuid})"
                )
                job.job_status = JobStatus.FAILED
        except Exception as e:
            trace = traceback.format_exc()
            self.logger.error(
                f"[{id}]Executing job failed with exception {job.task_uuid}: {trace} "
                f"(job_uuid {job.job_uuid})"
            )
            self.logger.error(f"[{id}]Error in executing task {job.task_uuid}: {e} ")
            job.job_status = JobStatus.FAILED
        except:
            trace = traceback.format_exc()
            self.logger.error(
                f"[{id}]Executing job failed with unknown error {job.task_uuid}: {trace} "
                f"(job_uuid {job.job_uuid})"
            )
            job.job_status = JobStatus.FAILED

    def _worker_initializes_job(self, id: int, job: Job) -> bool:
        task_uuid = job.task_uuid
        task_in_db = self.taskstore.get_task_by_uuid(task_uuid)
        if task_in_db is None:
            self.logger.error(f"[{id}]Task {task_uuid} not found in the task list")
            raise exceptions.EntityNotFoundException(f"{task_uuid}", "task")

        if task_in_db.is_deleted:
            self.logger.warning(f"[{id}]Task {task_uuid} is marked as deleted.")
            return False

        self.logger.info(
            f"[{id}]Got job from the queue with task_uuid {task_uuid} "
            f"with status {job.job_status} "
            f"(job_uuid {job.job_uuid})"
        )

        if job.job_status == JobStatus.COMPLETED:
            self.logger.warning(
                f"[{id}]Found a completed job_uuid {job.job_uuid} for task {task_uuid}."
            )
            self.taskstore.update_task_status(task_uuid, TaskStatus.COMPLETED)
            return False
        elif job.job_status == JobStatus.PAUSED:
            self.logger.warning(
                f"[{id}]Found a paused job_uuid {job.job_uuid} for task {task_uuid}."
            )
            self.taskstore.update_task_status(task_uuid, TaskStatus.PAUSED)
            return False
        elif job.job_status == JobStatus.ABORTED:
            self.logger.warning(
                f"[{id}]Found an aborted job_uuid {job.job_uuid} for task {task_uuid}."
            )
            self.taskstore.update_task_status(task_uuid, TaskStatus.ABORTED)
            return False
        elif job.job_status == JobStatus.RUNNING:
            self.logger.error(
                f"[{id}]Found a running job_uuid {job.job_uuid} for task {task_uuid}. This should not happen."
            )
            return False

        if (
            job.job_status == JobStatus.CREATED
            or job.job_status == JobStatus.PENDING
            or job.job_status == JobStatus.FAILED
        ):
            self.taskstore.update_task_status(task_uuid, TaskStatus.RUNNING)
            job.job_status = JobStatus.RUNNING
        else:
            raise ValueError(f"Unknown job status {job.job_status}")
        with self.lock:
            self.logger.noop("Inside the lock ...", noop_lvl=3)

            self.tasks_running[task_uuid] = job
            self.tasks_todo[task_uuid] = JobStatus.RUNNING
        self.logger.noop("Outside the lock ...", noop_lvl=3)
        return True

    def _worker_finalizes_job(self, id: int, job: Job) -> None:
        self.logger.info(
            f"Finalizing the job_uuid {job.job_uuid}, status {job.job_status}."
        )
        assert (
            job.job_status == JobStatus.RUNNING
            or job.job_status == JobStatus.COMPLETED
            or job.job_status == JobStatus.FAILED
            or job.job_status == JobStatus.ABORTED
        ), f"Job status is {job.job_status} while trying to finalize the job."

        if job.job_status == JobStatus.RUNNING:
            self.logger.error(
                f"[{id}]Found a running task run {job.job_uuid} "
                f"for task {job.task_uuid}. Mark it as failed."
            )
            job.job_status = JobStatus.FAILED

        with self.lock:
            self.logger.noop("Inside the lock ...", noop_lvl=3)
            self.tasks_running.pop(job.task_uuid)
            self.tasks_todo[job.task_uuid] = job.job_status
        self.logger.noop("Outside the lock ...", noop_lvl=3)

        if job.job_status == JobStatus.FAILED:
            self.logger.debug(
                f"Adding failed job {job.job_uuid} to the cooldown queue."
            )
            job.last_failed_at = time_utils.current_datetime()
            if job.retry_count is None:
                job.retry_count = 1
            else:
                job.retry_count = job.retry_count + 1

            with self.lock:
                self.logger.noop("Inside the lock ...", noop_lvl=3)
                self.tasks_in_cooldown_queue[job.task_uuid] = job
                self.cooldown_queue.put(job)
            self.logger.noop("Outside the lock ...", noop_lvl=3)

        self.taskstore.update_task_status(job.task_uuid, job.job_status)
        if job.job_status == JobStatus.COMPLETED:
            self.logger.debug(
                f"[{id}]Removing task {job.task_uuid} from tasks_all list."
            )
            self.tasks_todo.pop(job.task_uuid)
        self.logger.info(
            f"Finalizing the job_uuid {job.job_uuid} done, final status {job.job_status}."
        )

    # Worker function
    def _worker(self, id: int):
        self.logger.debug(f"[{id}] starting the worker thread.")
        should_run = True
        while should_run:
            job = self.task_queue.get()
            job_is_executable = False
            try:
                if job is None:
                    self.logger.info(
                        f"[{id}]Received None from the queue, shutting down the worker."
                    )
                    should_run = False
                    continue

                with self.lock:
                    self.logger.noop("Inside the lock ...", noop_lvl=3)
                    self.tasks_in_queue.pop(job.task_uuid)
                self.logger.noop("Outside the lock ...", noop_lvl=3)

                if self.status != SchedulerStatus.RUNNING:
                    self.logger.info(
                        f"Received a task but the scheduler status is {self.status}"
                    )
                    should_run = False
                    continue

                job_is_executable = self._worker_initializes_job(id, job)

                # TODO: executor to support pause / abort operations
                self.logger.debug(f"Executing job_uuid {job.job_uuid} ...")
                if job_is_executable:
                    self._worker_executes_job(id, job)
            except Exception as e:
                tb_str = traceback.format_exc()
                self.logger.error(f"[{id}]Critical error in the worker: {tb_str}")
            finally:
                self.logger.info(
                    f"[{id}]In the finally block job_uuid {job.job_uuid}, "
                    f"job_is_executable {job_is_executable}"
                )
                if job_is_executable:
                    self._worker_finalizes_job(id, job)
                self.task_queue.task_done()
        self.logger.info(f"[{id}]Finished the worker.")

    def _start_workers(self) -> None:
        self.logger.info("Starting the task loader and workers in the scheduler.")

        assert (
            self.status == SchedulerStatus.RUNNING
        ), f"Scheduler status is {self.status} while trying to start workers."
        assert (
            self.task_loader == None
        ), f"The task loader is not None while trying to start workers."
        self.task_loader = self.threadpool.submit(self._task_loader, interval=3)
        for id in range(self.num_of_workers):
            self.workers[id] = self.threadpool.submit(self._worker, id)
        self.logger.info(
            "The task loader and workers in the scheduler have been started."
        )

    def _stop_workers(self, force: bool = False) -> None:
        self.logger.info("Stopping the task loader and workers in the scheduler.")

        assert (
            self.status != SchedulerStatus.RUNNING
        ), f"Scheduler status is {self.status} while trying to stop workers."
        if self.task_loader is not None:
            if self.task_loader.running():
                self.task_loader.result()
            self.task_loader = None

        running_tasks = []
        for id in range(self.num_of_workers):
            if self.workers[id].running():
                self.logger.info(
                    f"[{id}] woker: {self.workers[id]}. Running : {self.workers[id].running()}"
                )
                running_tasks.append(id)
        for id in running_tasks:
            if force:
                self.workers[id].cancel()
                self.workers[id].result()
                self.logger.info(f"[{id}]In force mode, cancelled worker.")
            else:
                # the order the workers receiving the None signal is not guaranteed
                # so we can't do check and finish it one loop
                self.task_queue.put(None)

    def _check_workers_done(self) -> bool:
        assert (
            self.status != SchedulerStatus.RUNNING
        ), f"Scheduler status is {self.status} while trying to check workers done."
        done = True
        if self.task_loader is not None and self.task_loader.running():
            self.logger.info(f"Task loader is running.")
            done = False

        for id in range(self.num_of_workers):
            if self.workers[id].running():
                self.logger.info(f"Worker {id} is running.")
                done = False
            else:
                self.logger.info(f"Worker {id} is done.")
        return done

    def set_log_location(self, log_location: str) -> None:
        self.logger.log_to_dir(log_location, filename="scheduler.log")
        self.logger.remove_default_handler()

    def start(self) -> bool:
        self.logger.info("Starting the simple scheduler.")
        if self.status == SchedulerStatus.RUNNING:
            self.logger.warning("No-op: the scheduler is still running.")
            return False

        self._init_load_tasks()
        self.status = SchedulerStatus.RUNNING
        self._start_workers()
        self.logger.info("The simple scheduler has started.")
        self.context.scheduler_is_running = True
        return True

    def pause(self) -> bool:
        """
        Do not accept tasks any more, but let the current task finish.
        """
        if self.status != SchedulerStatus.RUNNING:
            self.logger.info(
                "No-op: trying to pause the scheduler that is not running."
            )
            return False

        self._clear_tasks()
        self.status = SchedulerStatus.PAUSED

        # todo: check if we need to wait for all workers to finish
        if self._check_workers_done() is False:
            self.logger.warning("Not all workers are done")
        return True

    def resume(self) -> bool:
        if self.status == SchedulerStatus.RUNNING:
            self.logger.info("No-op: trying to resume the scheduler that is running.")
            return False

        self._init_load_tasks()

        self.status = SchedulerStatus.RUNNING
        self._start_workers()
        return True

    def get_status(self) -> SchedulerStatus:
        return self.status

    def cooldown_tasks(self) -> Dict[str, Job]:
        return self.tasks_in_cooldown_queue

    def queued_tasks(self) -> Dict[str, Job]:
        return self.tasks_in_queue

    def running_tasks(self) -> Dict[str, Job]:
        return self.tasks_running

    def active_tasks(self) -> Dict[str, Job]:
        results: Dict[str, Job] = {}
        results.update(self.tasks_in_queue)
        results.update(self.tasks_running)
        results.update(self.tasks_in_cooldown_queue)
        return results

    def shutdown(self, force: bool = False):
        self.logger.info(
            f"Shutting down the simple scheduler, queue size: {self.task_queue.qsize()}"
        )
        self.status = SchedulerStatus.STOPPED

        self._clear_tasks()
        self._stop_workers(force)

        self.threadpool.shutdown(wait=False)
        self.context.scheduler_is_running = False
        self.logger.info("Finished simple scheduler shutdown.")

    def pause_task(self, task_uuid: str) -> None:
        raise NotImplementedError()

    def resume_task(self, task_uuid: str) -> None:
        raise NotImplementedError()

    def abort_task(self, task_uuid: str) -> None:
        raise NotImplementedError()

    def set_target_org(self, org: Org) -> None:
        self.target_org = org

    def set_target_kb(self, kb: KnowledgeBase) -> None:
        self.target_kb = kb

    def set_target_docsources(self, docsources: List[DocSource]) -> None:
        self.target_docsources = docsources
