import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.eds.scheduler.schemas.program import ProgramSpec

TASK_UUID_ATTR = "task_uuid"
TASK_STATUS_ATTR = "task_status"
TASK_DELETE_ATTR = "is_deleted"


class TaskSchedule(str, Enum):
    SIMPLE = "simple"
    RECURRING = "recurring"


class TaskStatus(str, Enum):
    CREATED = "created"  # the task has been created but no run has been started
    PENDING = "pending"  # the task run is in the queue
    RUNNING = "running"  # the task run is running
    PAUSED = "paused"  # the task run is paused
    COMPLETED = "completed"  # the task run is completed successfully
    FAILED = "failed"  # the task run has failed
    ABORTED = "aborted"  # the task run has been aborted


class TaskStatusDescription(BaseModel):
    status: TaskStatus
    display_name: str
    description: str


class TaskBase(BaseModel):
    org_id: str
    kb_id: str
    docsource_uuid: str

    # Add these two for easier search
    docsink_uuid: Optional[str] = None
    document_uuid: Optional[str] = None

    program_spec: ProgramSpec

    # TODO: we will support recurring tasks in the future
    task_type: Optional[TaskSchedule] = TaskSchedule.SIMPLE


class TaskCreate(TaskBase):
    pass


class TaskInDBBase(TaskBase):
    task_uuid: str
    task_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_deleted: Optional[bool] = False


class TaskUpdate(TaskInDBBase):
    pass


class TaskInDB(TaskInDBBase):
    @classmethod
    def from_task_create(TaskInDB, task_create: TaskCreate) -> "TaskInDB":
        ct = time_utils.current_datetime()
        task_in_db = TaskInDB(
            org_id=task_create.org_id,
            kb_id=task_create.kb_id,
            docsource_uuid=task_create.docsource_uuid,
            task_uuid="",
            program_spec=copy.deepcopy(task_create.program_spec),
            task_status=TaskStatus.CREATED,
            created_at=ct,
            updated_at=ct,
        )
        assign_properties(task_create, task_in_db)
        return task_in_db

    @classmethod
    def from_task_update(TaskInDB, task_update: TaskUpdate) -> "TaskInDB":
        # the uuid from the update should match the uuid in the db
        # which is checked from the caller of this function
        task_in_db = TaskInDB(
            org_id=task_update.org_id,
            kb_id=task_update.kb_id,
            docsource_uuid=task_update.docsource_uuid,
            program_spec=copy.deepcopy(task_update.program_spec),
            task_uuid=task_update.task_uuid,
            job_status=task_update.task_status,
            updated_at=time_utils.current_datetime(),
        )
        assign_properties(task_update, task_in_db)
        return task_in_db


@add_fieldname_constants
class Task(TaskInDBBase):

    @classmethod
    def get_task_status_descriptions(cls) -> list[TaskStatusDescription]:
        task_status_descriptions = [
            TaskStatusDescription(
                status=TaskStatus.CREATED,
                display_name="Created",
                description="The task has been created but no job has been started",
            ),
            TaskStatusDescription(
                status=TaskStatus.PENDING,
                display_name="Pending",
                description="The task is in the queue",
            ),
            TaskStatusDescription(
                status=TaskStatus.RUNNING,
                display_name="Running",
                description="The task is running",
            ),
            TaskStatusDescription(
                status=TaskStatus.PAUSED,
                display_name="Paused",
                description="The task is paused",
            ),
            TaskStatusDescription(
                status=TaskStatus.COMPLETED,
                display_name="Completed",
                description="The task is completed successfully",
            ),
            TaskStatusDescription(
                status=TaskStatus.FAILED,
                display_name="Failed",
                description="The task has failed",
            ),
            TaskStatusDescription(
                status=TaskStatus.ABORTED,
                display_name="Aborted",
                description="The task has been aborted",
            ),
        ]
        return task_status_descriptions

    @classmethod
    def from_task_in_db(Task, task_in_db: TaskInDB) -> "Task":
        task = Task(
            org_id=task_in_db.org_id,
            kb_id=task_in_db.kb_id,
            program_spec=copy.deepcopy(task_in_db.program_spec),
            task_uuid=task_in_db.task_uuid,
            docsource_uuid=task_in_db.docsource_uuid,
            job_status=task_in_db.task_status,
            is_deleted=task_in_db.is_deleted,
        )
        assign_properties(task_in_db, task)

        return task


@dataclass
class BaseTaskSchema(ABC):
    """Abstract base schema for task implementations."""

    TABLE_NAME: str = "task"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        """Get base column definitions shared across implementations."""
        return {
            Task.FIELD_ORG_ID: "VARCHAR",
            Task.FIELD_KB_ID: "VARCHAR",
            Task.FIELD_DOCSOURCE_UUID: "VARCHAR",
            Task.FIELD_DOCSINK_UUID: "VARCHAR",
            Task.FIELD_DOCUMENT_UUID: "VARCHAR",
            Task.FIELD_PROGRAM_SPEC: "VARCHAR",
            Task.FIELD_TASK_TYPE: "VARCHAR",
            Task.FIELD_TASK_UUID: "VARCHAR PRIMARY KEY",
            Task.FIELD_TASK_STATUS: "VARCHAR",
            Task.FIELD_CREATED_AT: "TIMESTAMP",
            Task.FIELD_UPDATED_AT: "TIMESTAMP",
            Task.FIELD_IS_DELETED: "BOOLEAN DEFAULT FALSE",
        }
