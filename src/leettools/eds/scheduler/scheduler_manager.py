import os
import threading
import time
from pathlib import Path
from typing import List, Optional

import psutil

from leettools.common.exceptions import UnexpectedCaseException
from leettools.common.logging import logger
from leettools.common.singleton_meta import SingletonMeta
from leettools.context_manager import Context
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.scheduler import AbstractScheduler
from leettools.settings import SystemSettings


def _is_process_running(pid: int) -> bool:
    """
    Check if a process with the given PID is running.

    :param pid: Process ID to check
    :return: True if the process is running, False otherwise
    """
    try:
        process = psutil.Process(pid)
        if process.name().startswith("python3.9"):
            return True
        # in container, it is possible that another running process has the same PID
        # as the previous scheduler process
        logger().info(
            f"Process with PID {pid} with name {process.name()} is not a python process."
        )
        return False
    except psutil.NoSuchProcess:
        return False


def _read_lock_file(lock_file: str) -> Optional[int]:
    """
    Read the PID from the lock file if it exists.

    :param lock_file: Path to the lock file
    :return: PID if the lock file exists and is valid, None otherwise
    """
    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r", encoding="utf-8") as file:
                pid = int(file.read().strip())
                return pid
        except (IOError, ValueError):
            return None
    return None


def _write_lock_file(lock_file: str, pid: int) -> None:
    """
    Write the current PID to the lock file.

    :param lock_file: Path to the lock file
    :param pid: Current process ID to write
    """
    with open(lock_file, "w", encoding="utf-8") as file:
        file.write(str(pid))


def _check_lock_file(lock_file: str) -> bool:
    """
    Check if the lock file is valid.

    This function is run only once in the Singleton constructor.

    :param lock_file: Path to the lock file
    :return: True if the lock file is valid, False otherwise
    """
    current_pid = os.getpid()
    existing_pid = _read_lock_file(lock_file)

    if existing_pid is None:
        logger().info("No existing lock file found. Starting scheduler...")
        _write_lock_file(lock_file, current_pid)
        return True
    else:
        if _is_process_running(existing_pid):
            if existing_pid != current_pid:
                logger().info(
                    f"Scheduler with PID {existing_pid} is already running. Exiting."
                )
                return False
            else:
                logger().warning(
                    f"Scheduler with current PID {existing_pid} is already running. "
                    "If it running in a container, it is possible that the previous run "
                    "has the same PID as the current run. Continuing..."
                )
                return True
        else:
            logger().info(
                f"Scheduler with PID {existing_pid} is not running. Starting service..."
            )
            _write_lock_file(lock_file, current_pid)
            return True


def _get_lock_file(settings: SystemSettings) -> str:
    return f"{settings.LOG_ROOT}/scheduler.lock"


def _should_run_service(settings: SystemSettings) -> bool:
    """
    This function is run only once in the Singleton constructor.
    """
    lock_file = _get_lock_file(settings)
    Path(settings.LOG_ROOT).mkdir(parents=True, exist_ok=True)
    logger().info(f"The scheduler lock file is {lock_file}.")
    return _check_lock_file(lock_file=lock_file)


class SingletonMetaSchedule(SingletonMeta):
    _lock: threading.Lock = threading.Lock()


class SchedulerManager(metaclass=SingletonMetaSchedule):

    # right now passing in different context will not create a new instance
    def __init__(self, context: Context):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            settings = context.settings
            if not _should_run_service(settings):
                raise UnexpectedCaseException(
                    f"Another scheduler service is running."
                    f"Check {_get_lock_file(settings)} for the PID."
                )

            num_of_workers = settings.scheduler_default_number_worker
            if num_of_workers > 32 or num_of_workers < 4:
                logger().warning(
                    f"Invalid number of workers {num_of_workers}. Must be between 4 and 32."
                    "Setting the number of workers to 4."
                )
                num_of_workers = 4

            logger().info(f"Creating a new scheduler with {num_of_workers} workers.")

            from leettools.eds.scheduler._impl.scheduler_simple import SchedulerSimple

            self._scheduler = SchedulerSimple(
                context=context, num_of_workers=num_of_workers
            )

    def get_scheduler(self) -> AbstractScheduler:
        return self._scheduler


def _print_scheduler_status(scheduler: AbstractScheduler) -> None:
    logger().info(f"Scheduler status is {scheduler.get_status()}")
    logger().info(f"Queued tasks: {len(scheduler.queued_tasks())}")
    logger().info(f"Running tasks: {len(scheduler.running_tasks())}")
    logger().info(f"Cooldown tasks: {len(scheduler.cooldown_tasks())}")


def run_scheduler(
    context: Context,
    org: Optional[Org] = None,
    kb: Optional[KnowledgeBase] = None,
    docsources: Optional[List[DocSource]] = None,
) -> bool:
    """
    This function runs a scheduler and waits for its to finish.

    If another scheduler is already running, this function will exit and return false.

    Args:
    - context: The context object
    - org: if specified, only process this organization
    - kb: if specified, only process this knowledge base
    - docsources: if specified, only process this docsrc
    """

    if context.is_svc == True:
        logger().info("Running inside the service, no need to run the scheduler.")
        # the following should be an no-op
        scheduler_manager = SchedulerManager(context)
        assert scheduler_manager.get_scheduler() is not None
        return False

    logger().info("[run_scheduler]Getting the scheduler from SchedulerManager.")
    try:
        scheduler_manager = SchedulerManager(context)  # type: SchedulerManager
    except UnexpectedCaseException as e:
        # this is possible in the manual run case
        # basically another scheduler is already running
        logger().info(f"Another scheduler is already running. No need to run.")
        return False

    scheduler = scheduler_manager.get_scheduler()
    scheduler.set_target_org(org)
    scheduler.set_target_kb(kb)
    scheduler.set_target_docsources(docsources)

    logger().info("[run_scheduler]Starting the scheduler.")
    scheduler.start()

    # TODO: we need to allow the task_scanner enough time to pick up the tasks
    time.sleep(15)

    try:
        _print_scheduler_status(scheduler)
        active_tasks = scheduler.active_tasks()
        while len(active_tasks) > 0:
            _print_scheduler_status(scheduler)
            time.sleep(5)
            active_tasks = scheduler.active_tasks()

        logger().info("Finished running the task.")
    finally:
        scheduler.shutdown()
        Path(_get_lock_file(context.settings)).unlink()

    return True


if __name__ == "__main__":
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    context.is_svc = False
    run_scheduler(context)
