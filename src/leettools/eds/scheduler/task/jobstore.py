from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.common.utils import factory_util
from leettools.eds.scheduler.schemas.job import Job, JobCreate, JobUpdate
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.settings import SystemSettings


class AbstractJobStore(ABC):

    @abstractmethod
    def create_job(self, job_create: JobCreate) -> Optional[Job]:
        pass

    @abstractmethod
    def get_all_jobs_for_task(self, task_uuid: str) -> List[Job]:
        pass

    @abstractmethod
    def get_the_latest_job_for_task(self, task_uuid: str) -> Optional[Job]:
        pass

    @abstractmethod
    def get_job(self, job_uuid: str) -> Optional[Job]:
        pass

    @abstractmethod
    def update_job(self, job_update: JobUpdate) -> Optional[Job]:
        pass

    @abstractmethod
    def delete_job(self, job_uuid: str) -> bool:
        pass

    @abstractmethod
    def update_job_status(self, job_uuid: str, job_status: JobStatus) -> Job:
        pass

    @abstractmethod
    def _reset_for_test(self) -> None:
        """
        Reset the store for testing.
        """
        pass


def create_jobstore(settings: SystemSettings) -> AbstractJobStore:
    """
    Create a TaskStore based on the settings.

    Args:
    settings: The system settings.

    Returns:
    The TaskStore.
    """
    return factory_util.create_manager_with_repo_type(
        manager_name="jobstore",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractJobStore,
        settings=settings,
    )
