from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.eds.scheduler.schemas.program import ProgramSpec

"""
See [README](./README.md) about the usage of different pydantic models.
"""

"""
Each task may have multiple jobs associated with it. Each job is a specific run of the task.
"""


# Shared properties
class JobBase(BaseModel):
    task_uuid: str = Field(..., description="The UUID of the task.")
    program_spec: ProgramSpec = Field(
        ...,
        description=(
            "The parameters needed to run the task. A new job will created based on the "
            "task_uuid and the spec."
        ),
    )


class JobCreate(JobBase):
    pass


class JobInDBBase(JobBase):
    job_uuid: str = Field(..., description="The UUID of the job.")
    job_status: Optional[JobStatus] = Field(None, description="The status of the job.")
    progress: Optional[float] = Field(
        None, description="The progress percentage of the job."
    )
    result: Optional[Dict] = Field(None, description="The result of the job.")
    log_location: Optional[str] = Field(
        None, description="The location of the log file."
    )
    output_dir: Optional[str] = Field(None, description="The location of the output.")
    paused_at: Optional[datetime] = Field(None, description="The pause time.")
    last_failed_at: Optional[datetime] = Field(
        None, description="The last failed time."
    )
    retry_count: Optional[int] = Field(None, description="The retry count.")
    is_deleted: Optional[bool] = Field(False, description="The deletion flag.")


class JobUpdate(JobInDBBase):
    pass


# Properties properties stored in DB
class JobInDB(JobInDBBase):

    created_at: Optional[datetime] = Field(None, description="The creation time.")
    updated_at: Optional[datetime] = Field(None, description="The update time.")

    @classmethod
    def from_job_create(JobInDB, job_create: JobCreate) -> "JobInDB":
        ct = time_utils.current_datetime()
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
            updated_at=time_utils.current_datetime(),
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
        with open(self.log_location, "a+", encoding="utf-8") as f:
            f.write(
                f"Job log for {job_uuid} created at {time_utils.current_datetime()}\n"
            )


# Properties to return to client
@add_fieldname_constants
class Job(JobInDB):

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
