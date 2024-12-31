from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from leettools.context_manager import Context
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.schemas.job import Job
from leettools.eds.scheduler.schemas.scheduler_status import SchedulerStatus


class AbstractScheduler(ABC):
    """
    This is the abstract class for all schedulers.
    We can use scheduler such as volcano, airflow, prefect, etc.
    """

    @abstractmethod
    def __init__(
        self,
        context: Context,
    ) -> None:
        """
        The scheduler constructor. Should support the following parameters:
        - context: The context object
        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """
        Start the scheduler, return True if actually performed the starting operation,
        False if the scheduler is still running.
        """
        pass

    @abstractmethod
    def get_status(self) -> SchedulerStatus:
        pass

    @abstractmethod
    def pause(self) -> bool:
        """
        Pause the scheduler, return True if actually performed the pause operation,
        False if the scheduler is not running.
        """
        pass

    @abstractmethod
    def resume(self) -> bool:
        """
        Resume the scheduler, return True if actually performed the resume operation,
        False if the scheduler is still running.
        """
        pass

    @abstractmethod
    def set_log_location(self, log_location: str) -> None:
        """
        Set the location of the log file.

        Args:
        log_location: The location of the log file.
        """
        pass

    @abstractmethod
    def shutdown(sel, force: bool = False) -> None:
        """
        Shut down the executor. If force is True, the executor will be shut down even if
        there are items running, usually used in automated tests so that it doesn't
        block the process.
        """
        pass

    @abstractmethod
    def pause_task(self, task_uuid: str) -> None:
        pass

    @abstractmethod
    def resume_task(self, task_uuid: str) -> None:
        pass

    @abstractmethod
    def abort_task(self, task_uuid: str) -> None:
        pass

    @abstractmethod
    def queued_tasks(self) -> Dict[str, Job]:
        """
        Return all tasks in queue, the key is the task_uuid, the value is the job.
        """
        pass

    @abstractmethod
    def running_tasks(self) -> Dict[str, Job]:
        """
        Return all running tasks, the key is the task_uuid, the value is the job.
        """
        pass

    @abstractmethod
    def cooldown_tasks(self) -> Dict[str, Job]:
        """
        Return all cooldown tasks, the key is the task_uuid, the value is the job.
        """
        pass

    @abstractmethod
    def active_tasks(self) -> Dict[str, Job]:
        """
        Return all active tasks, including jobs in the queue, running jobs, and jobs in
        cooldown queue. the key is the task_uuid, the value is the job.
        """
        pass

    @abstractmethod
    def set_target_org(self, org: Org) -> None:
        """
        Set the target organization for the scheduler.
        """
        pass

    @abstractmethod
    def set_target_kb(self, kb: KnowledgeBase) -> None:
        """
        Set the target knowledge base for the scheduler.
        """
        pass

    @abstractmethod
    def set_target_docsources(self, docsources: List[DocSource]) -> None:
        """
        Set the target docsources for the scheduler.
        """
        pass
