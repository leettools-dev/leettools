import uuid
from typing import Any, Dict, List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.exceptions import EntityNotFoundException, UnexpectedCaseException
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.schemas.program import ProgramSpec
from leettools.eds.scheduler.schemas.task import (
    Task,
    TaskCreate,
    TaskInDB,
    TaskStatus,
    TaskUpdate,
)
from leettools.eds.scheduler.task._impl.duckdb.taskstore_duckdb_schema import (
    TaskDuckDBSchema,
)
from leettools.eds.scheduler.task.taskstore import AbstractTaskStore
from leettools.settings import SystemSettings


class TaskStoreDuckDB(AbstractTaskStore):
    """
    TaskStoreDuckDB is a TaskStore implementation using
    DuckDB as the backend.
    """

    def __init__(self, settings: SystemSettings) -> None:
        """
        Initialize the DuckDB Taskstore.
        """
        logger().info(f"TaskStoreDuckDB: initializing")
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)
        self.table_name = self._get_table_name()

    def _dict_to_task(self, task_dict: Dict[str, Any]) -> Task:
        task_dict = task_dict.copy()
        if Task.FIELD_PROGRAM_SPEC in task_dict:
            task_dict[Task.FIELD_PROGRAM_SPEC] = ProgramSpec.model_validate_json(
                task_dict[Task.FIELD_PROGRAM_SPEC]
            )
        return Task.model_validate(task_dict)

    def _get_table_name(self) -> str:
        """Get the table name."""
        return self.duckdb_client.create_table_if_not_exists(
            self.settings.DB_TASKS,
            TaskDuckDBSchema.TABLE_NAME,
            TaskDuckDBSchema.get_schema(),
        )

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        task_dict = task.model_dump()
        if Task.FIELD_PROGRAM_SPEC in task_dict:
            task_dict[Task.FIELD_PROGRAM_SPEC] = ProgramSpec.model_validate(
                task_dict[Task.FIELD_PROGRAM_SPEC]
            ).model_dump_json()
        return task_dict

    def create_task(self, task_create: TaskCreate) -> Task:
        task_in_db = TaskInDB.from_task_create(task_create)
        task_dict = self._task_to_dict(task_in_db)
        task_dict[Task.FIELD_TASK_UUID] = str(uuid.uuid4())
        column_list = list(task_dict.keys())
        value_list = list(task_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
        )
        task_in_db.task_uuid = task_dict[Task.FIELD_TASK_UUID]
        return self.update_task(task_in_db)

    def delete_task(self, task_uuid: str) -> bool:

        task = self.get_task_by_uuid(task_uuid)
        if task is None:
            raise EntityNotFoundException(entity_name=task_uuid, entity_type="Task")

        task.is_deleted = True
        task.updated_at = time_utils.current_datetime()

        task_dict = self._task_to_dict(task)
        task_uuid = task_dict.pop(Task.FIELD_TASK_UUID)
        column_list = list(task_dict.keys())
        value_list = list(task_dict.values()) + [task_uuid]
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=f"WHERE {Task.FIELD_TASK_UUID} = ?",
        )

        from leettools.context_manager import Context, ContextManager

        context = ContextManager().get_context()  # type: Context
        job_store = context.get_task_manager().get_jobstore()
        jobs = job_store.get_all_jobs_for_task(task_uuid)
        for job in jobs:
            job_store.delete_job(job.job_uuid)
        return True

    def get_all_tasks(self) -> List[Task]:
        where_clause = f"WHERE {Task.FIELD_IS_DELETED}=FALSE"
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
        )
        return [self._dict_to_task(dict(rtn_list[i])) for i in range(len(rtn_list))]

    def get_all_tasks_for_org(self, org: Org) -> List[Task]:
        where_clause = f"""
            WHERE {Task.FIELD_ORG_ID}=? AND {Task.FIELD_IS_DELETED}=FALSE
        """
        value_list = [org.org_id]
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_task(dict(rtn_list[i])) for i in range(len(rtn_list))]

    def get_all_tasks_for_kb(self, org: Org, kb: KnowledgeBase) -> List[Task]:
        where_clause = f"""
            WHERE {Task.FIELD_KB_ID}=? AND {Task.FIELD_ORG_ID}=? AND {Task.FIELD_IS_DELETED}=FALSE
        """
        logger().info(f"get_all_tasks_for_kb: {kb.kb_id}, {org.org_id}")
        value_list = [kb.kb_id, org.org_id]
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        logger().info(f"get_all_tasks_for_kb: {len(rtn_list)}")
        return [self._dict_to_task(dict(rtn_list[i])) for i in range(len(rtn_list))]

    def get_incomplete_tasks(self) -> List[Task]:
        """
        Get all incomplete tasks: not completed or aborted.

        Returns:
        The incomplete tasks that need to be processed.

        Right now both completed and aborted tasks are considered as complete.
        """
        where_clause = f"""
            WHERE {Task.FIELD_TASK_STATUS} != ? AND {Task.FIELD_IS_DELETED}=FALSE
        """
        value_list = [TaskStatus.COMPLETED]
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_task(dict(rtn_list[i])) for i in range(len(rtn_list))]

    def get_task_by_uuid(self, task_uuid: str) -> Optional[Task]:
        where_clause = f"WHERE {Task.FIELD_TASK_UUID}=?"
        value_list = [task_uuid]
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if len(rtn_list) > 1:
            logger().error(f"Found multiple tasks with UUID {task_uuid}!")
            raise UnexpectedCaseException(
                f"Found multiple tasks with UUID {task_uuid}!"
            )
        elif len(rtn_list) == 0:
            return None
        else:
            return self._dict_to_task(dict(rtn_list[0]))

    def get_tasks_for_docsink(self, docsink_uuid: str) -> List[Task]:
        where_clause = f"""
            WHERE {DocSink.FIELD_DOCSINK_UUID}=? AND {Task.FIELD_IS_DELETED}=FALSE
        """
        value_list = [docsink_uuid]
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_task(dict(rtn_list[i])) for i in range(len(rtn_list))]

    def get_tasks_for_docsource(self, docsource_uuid: str) -> List[Task]:
        where_clause = f"""
            WHERE {DocSource.FIELD_DOCSOURCE_UUID}=? AND {Task.FIELD_IS_DELETED}=FALSE
        """
        value_list = [docsource_uuid]
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_task(dict(rtn_list[i])) for i in range(len(rtn_list))]

    def get_tasks_for_document(self, document_uuid: str) -> List[Task]:
        where_clause = f"""
            WHERE {Document.FIELD_DOCUMENT_UUID}=? AND {Task.FIELD_IS_DELETED}=FALSE
        """
        value_list = [document_uuid]
        rtn_list = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_task(dict(rtn_list[i])) for i in range(len(rtn_list))]

    def update_task(self, task_update: TaskUpdate) -> Task:
        """
        Update a task.

        Args:
        task_update: The task to update.

        Returns:
        The updated task.
        """
        existing_task = self.get_task_by_uuid(task_update.task_uuid)
        if existing_task is None:
            raise EntityNotFoundException(
                entity_name=task_update.task_uuid, entity_type="Task"
            )
        task = TaskInDB.from_task_update(task_update)
        task_dict = self._task_to_dict(task)
        task_uuid = task_dict.pop(Task.FIELD_TASK_UUID)
        column_list = list(task_dict.keys())
        value_list = list(task_dict.values()) + [task_uuid]
        where_clause = f"WHERE {Task.FIELD_TASK_UUID}=?"
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_task_by_uuid(task_uuid)

    def update_task_status(self, task_uuid: str, job_status: str) -> None:
        """
        Update the status of a task.

        Args:
        - task_uuid: The id of the task.
        - job_status: The new status.

        Returns:
        - The updated task.
        """
        column_list = [Task.FIELD_TASK_STATUS, Task.FIELD_UPDATED_AT]
        value_list = [job_status, time_utils.current_datetime()] + [task_uuid]
        where_clause = f"WHERE {Task.FIELD_TASK_UUID}=?"
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_task_by_uuid(task_uuid)

    def _reset_for_test(self) -> None:
        assert self.settings.DUCKDB_FILE == "duckdb_test.db"
        self.duckdb_client.delete_from_table(table_name=self.table_name)
