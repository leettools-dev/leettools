from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.eds.scheduler.schemas.program import ProgramSpec

JOB_UUID_ATTR = "job_uuid"
JOB_STATUS_ATTR = "job_status"
UPDATED_AT_ATTR = "updated_at"
JOB_DELETE_ATTR = "is_deleted"


class JobStatus(str, Enum):
    CREATED = "created"  # the task has been created but no job has been started
    PENDING = "pending"  # the job is in the queue
    RUNNING = "running"  # the job is running
    PAUSED = "paused"  # the job is paused
    COMPLETED = "completed"  # the kob is completed successfully
    FAILED = "failed"  # the job has failed
    ABORTED = "aborted"  # the job has been aborted


class JobStatusDescription(BaseModel):
    status: JobStatus
    display_name: str
    description: str


# Shared properties
class JobBase(BaseModel):
    task_uuid: str
    program_spec: ProgramSpec


class JobCreate(JobBase):
    pass


# Properties shared by models stored in DB
class JobInDBBase(JobBase):
    job_uuid: str
    job_status: Optional[JobStatus] = None
    progress: Optional[float] = None
    result: Optional[Dict] = None
    log_location: Optional[str] = None
    output_dir: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    last_failed_at: Optional[datetime] = None
    retry_count: Optional[int] = None
    is_deleted: Optional[bool] = False


class JobUpdate(JobInDBBase):
    pass


# Properties properties stored in DB
class JobInDB(JobInDBBase):
    @classmethod
    def from_job_create(JobInDB, job_create: JobCreate) -> "JobInDB":
        ct = datetime.now()
        job_in_db = JobInDB(
            task_uuid=job_create.task_uuid,
            program_spec=job_create.program_spec,
            job_uuid="",
            job_status=JobStatus.PENDING,
            created_at=ct,
            updated_at=ct,
        )
        assign_properties(job_create, job_in_db)
        return job_in_db

    @classmethod
    def from_job_update(JobInDB, job_update: JobUpdate) -> "JobInDB":
        job_in_db = JobInDB(
            task_uuid=job_update.task_uuid,
            program_spec=job_update.program_spec,
            job_uuid=job_update.job_uuid,
            job_status=job_update.job_status,
            updated_at=datetime.now(),
            progress=job_update.progress,
        )
        assign_properties(job_update, job_in_db)
        return job_in_db

    def set_job_uuid(self, job_uuid: str):
        from leettools.common.logging.log_location import LogLocator

        self.job_uuid = job_uuid
        log_dir = LogLocator.get_log_dir_for_task(
            task_uuid=self.task_uuid,
            job_uuid=job_uuid,
        )
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)

        self.log_location = f"{log_dir}/job.log"
        # make sure the file exists for log streaming
        # append mode will create the file if it does not exist
        with open(self.log_location, "a+") as f:
            f.write(f"Job log for {job_uuid} created at {datetime.now()}\n")


# Properties to return to client
@add_fieldname_constants
class Job(JobInDBBase):

    @classmethod
    def get_job_status_descriptions(cls) -> list[JobStatusDescription]:
        job_status_descriptions = [
            JobStatusDescription(
                status=JobStatus.CREATED,
                display_name="Created",
                description="The job has been created.",
            ),
            JobStatusDescription(
                status=JobStatus.PENDING,
                display_name="Pending",
                description="The job is in the queue",
            ),
            JobStatusDescription(
                status=JobStatus.RUNNING,
                display_name="Running",
                description="The job is running",
            ),
            JobStatusDescription(
                status=JobStatus.PAUSED,
                display_name="Paused",
                description="The job is paused",
            ),
            JobStatusDescription(
                status=JobStatus.COMPLETED,
                display_name="Completed",
                description="The job has completed successfully",
            ),
            JobStatusDescription(
                status=JobStatus.FAILED,
                display_name="Failed",
                description="The job has failed",
            ),
            JobStatusDescription(
                status=JobStatus.ABORTED,
                display_name="Aborted",
                description="The job has been aborted",
            ),
        ]
        return job_status_descriptions

    @classmethod
    def from_job_in_db(Job, job_in_db: JobInDB) -> "Job":
        # Note: we need to assign all the required properties and
        # properties with non-None default values, since assign_properties
        # will not override them if they are not None
        job = Job(
            task_uuid=job_in_db.task_uuid,
            program_spec=job_in_db.program_spec,
            job_uuid=job_in_db.job_uuid,
            job_status=job_in_db.job_status,
            updated_at=job_in_db.updated_at,
            is_deleted=job_in_db.is_deleted,
        )
        assign_properties(job_in_db, job)
        return job


@dataclass
class BaseJobSchema(ABC):
    TABLE_NAME: str = "job"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, str]:
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        return {
            Job.FIELD_TASK_UUID: "VARCHAR",
            Job.FIELD_PROGRAM_SPEC: "VARCHAR",
            Job.FIELD_JOB_UUID: "VARCHAR",
            Job.FIELD_JOB_STATUS: "VARCHAR",
            Job.FIELD_PROGRESS: "FLOAT",
            Job.FIELD_RESULT: "VARCHAR",
            Job.FIELD_LOG_LOCATION: "VARCHAR",
            Job.FIELD_OUTPUT_DIR: "VARCHAR",
            Job.FIELD_CREATED_AT: "TIMESTAMP",
            Job.FIELD_UPDATED_AT: "TIMESTAMP",
            Job.FIELD_PAUSED_AT: "TIMESTAMP",
            Job.FIELD_LAST_FAILED_AT: "TIMESTAMP",
            Job.FIELD_RETRY_COUNT: "INT",
            Job.FIELD_IS_DELETED: "BOOLEAN",
        }
