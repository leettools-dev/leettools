from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.common.utils import factory_util
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.schemas.task import Task, TaskCreate, TaskUpdate
from leettools.settings import SystemSettings


class AbstractTaskStore(ABC):

    @abstractmethod
    def create_task(self, task_create: TaskCreate) -> Task:
        """
        Add a task to the store.

        Args:
        - task_create: The task to be added.

        Returns:
        - The added task.
        """
        pass

    @abstractmethod
    def get_tasks_for_docsource(self, docsource_uuid: str) -> List[Task]:
        """
        Get all tasks for a docsource, including all its docsinks and documents.

        Args:
        - docsource_uuid: The id of the docsource.

        Returns:
        - The tasks.
        """
        pass

    @abstractmethod
    def get_tasks_for_docsink(self, docsink_uuid: str) -> List[Task]:
        """
        Get all tasks for a docsink, including all its documents.

        Args:
        - docsink_uuid: The id of the docsink.

        Returns:
        - The list of tasks.
        """
        pass

    @abstractmethod
    def get_tasks_for_document(self, document_uuid: str) -> List[Task]:
        """
        Get all tasks for a document.

        Args:
        - document_uuid: The id of the document.

        Returns:
        - The list of tasks.
        """
        pass

    @abstractmethod
    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks.

        Returns:
        - the list of all the tasks.
        """
        pass

    @abstractmethod
    def get_all_tasks_for_org(self, org: Org) -> List[Task]:
        """
        Get all tasks for an organization.

        Args:
        - org: The organization.

        Returns:
        - The list of tasks.
        """
        pass

    @abstractmethod
    def get_all_tasks_for_kb(self, org: Org, kb: KnowledgeBase) -> List[Task]:
        """
        Get all tasks for a knowledgebase.

        Args:
        - org: The organization.
        - kb: The knowledgebase.

        Returns:
        - The list of tasks.
        """
        pass

    @abstractmethod
    def get_incomplete_tasks(self) -> List[Task]:
        """
        Get all incomplete tasks.

        Returns:
        - The incomplete tasks.
        """
        pass

    @abstractmethod
    def get_task_by_uuid(self, task_uuid: str) -> Optional[Task]:
        """
        Get a task by its uuid. Will return the task even if it is marked as deleted.

        Args:
        - task_uuid: The id of the task.

        Returns:
        - The task.
        """
        pass

    @abstractmethod
    def update_task(self, task_update: TaskUpdate) -> Task:
        """
        Update a task.

        Args:
        - task_update: The task to be updated.

        Returns:
        - The updated task.
        """
        pass

    @abstractmethod
    def update_task_status(self, task_uuid: str, job_status: str) -> None:
        """
        Update the status of a task.

        Args:
        - task_uuid: The id of the task.
        - job_status: The new status.

        Returns:
        - The updated task.
        """
        pass

    @abstractmethod
    def delete_task(self, task_uuid: str) -> bool:
        """
        Delete a task.

        Args:
        - task_uuid: The id of the task.

        Returns:
        - True if the task was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def _reset_for_test(self) -> None:
        """
        Reset the task store for testing.
        """
        pass


def create_taskstore(settings: SystemSettings) -> AbstractTaskStore:
    """
    Create a TaskStore based on the settings.

    Args:
    - settings: The system settings.

    Returns:
    - The TaskStore.
    """
    return factory_util.create_manager_with_repo_type(
        manager_name="taskstore",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractTaskStore,
        settings=settings,
    )
