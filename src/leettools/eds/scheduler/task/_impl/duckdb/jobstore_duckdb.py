import uuid
from typing import Any, Dict, List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.exceptions import EntityNotFoundException
from leettools.common.utils import time_utils
from leettools.eds.scheduler.schemas.job import Job, JobCreate, JobInDB, JobUpdate
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.eds.scheduler.schemas.program import ProgramSpec
from leettools.eds.scheduler.task._impl.duckdb.jobstore_duckdb_schema import (
    JobDuckDBSchema,
)
from leettools.eds.scheduler.task.jobstore import AbstractJobStore
from leettools.settings import SystemSettings


class JobStoreDuckDB(AbstractJobStore):
    """
    JobStoreDuckDB is a JobStore implementation using
    DuckDB as the backend.
    """

    def __init__(self, settings: SystemSettings) -> None:
        """
        Initialize the DuckDB Jobstore.
        """
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)
        self.table_name = self._get_table_name()

    def _dict_to_job(self, job_dict: Dict[str, Any]) -> Job:
        job_dict = job_dict.copy()
        if Job.FIELD_PROGRAM_SPEC in job_dict:
            job_dict[Job.FIELD_PROGRAM_SPEC] = ProgramSpec.model_validate_json(
                job_dict[Job.FIELD_PROGRAM_SPEC]
            )
        return Job.model_validate(job_dict)

    def _get_table_name(self) -> str:
        """Get the table name."""
        return self.duckdb_client.create_table_if_not_exists(
            self.settings.DB_TASKS,
            JobDuckDBSchema.TABLE_NAME,
            JobDuckDBSchema.get_schema(),
        )

    def _job_to_dict(self, job: Job) -> Dict[str, Any]:
        job_dict = job.model_dump()
        if Job.FIELD_PROGRAM_SPEC in job_dict:
            job_dict[Job.FIELD_PROGRAM_SPEC] = ProgramSpec.model_validate(
                job_dict[Job.FIELD_PROGRAM_SPEC]
            ).model_dump_json()
        return job_dict

    def create_job(self, job_create: JobCreate) -> Optional[Job]:
        """
        Create a new job.

        Args:
        job_create: The job to create.

        Returns:
        The created job.
        """
        job_in_db = JobInDB.from_job_create(job_create)
        job_dict = self._job_to_dict(job_in_db)
        job_dict[Job.FIELD_JOB_UUID] = str(uuid.uuid4())
        column_list = list(job_dict.keys())
        value_list = list(job_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
        )
        job_in_db.set_job_uuid(job_dict[Job.FIELD_JOB_UUID])
        return self.update_job(job_in_db)

    def delete_job(self, job_uuid: str) -> bool:
        """
        Delete a job.

        Args:
        job_uuid: The job UUID.
        """
        existing_job = self.get_job(job_uuid)
        if existing_job is None:
            raise EntityNotFoundException(entity_name=job_uuid, entity_type="Job")

        existing_job.is_deleted = True
        existing_job.updated_at = time_utils.current_datetime()

        job_dict = self._job_to_dict(existing_job)
        job_uuid = job_dict.pop(Job.FIELD_JOB_UUID)
        column_list = list(job_dict.keys())
        value_list = list(job_dict.values()) + [job_uuid]
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=f"WHERE {Job.FIELD_JOB_UUID} = ?",
        )
        return True

    def get_all_jobs_for_task(self, task_uuid: str) -> List[Job]:
        """
        Get all jobs for a task.

        Args:
        task_uuid: The task UUID.

        Returns:
        The list of jobs.
        """
        where_clause = (
            f"WHERE {Job.FIELD_TASK_UUID} = ? AND {Job.FIELD_IS_DELETED} = FALSE"
        )
        value_list = [task_uuid]
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_job(rtn_dict) for rtn_dict in rtn_dicts]

    def get_job(self, job_uuid: str) -> Optional[Job]:
        """
        Get a job by UUID.

        Args:
        job_uuid: The job UUID.

        Returns:
        The job.
        """
        where_clause = f"WHERE {Job.FIELD_JOB_UUID} = ?"
        value_list = [job_uuid]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if rtn_dict is None:
            return None
        return self._dict_to_job(rtn_dict)

    def get_the_latest_job_for_task(self, task_uuid: str) -> Optional[Job]:
        """
        Get the latest job for a task.

        Args:
        task_uuid: The task UUID.

        Returns:
        The latest job.
        """
        where_clause = (
            f"WHERE {Job.FIELD_TASK_UUID} = ? AND {Job.FIELD_IS_DELETED} = FALSE "
            f"ORDER BY {Job.FIELD_UPDATED_AT} DESC LIMIT 1"
        )
        value_list = [task_uuid]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if rtn_dict is None:
            return None
        return self._dict_to_job(rtn_dict)

    def update_job(self, job_update: JobUpdate) -> Job:
        """
        Update a job.

        Args:
        job_update: The updated job.

        Returns:
        The updated job.
        """
        existing_job = self.get_job(job_update.job_uuid)
        if existing_job is None:
            raise EntityNotFoundException(
                entity_name=job_update.job_uuid, entity_type="Job"
            )

        job_in_db = JobInDB.from_job_update(job_update)
        job_dict = self._job_to_dict(job_in_db)
        job_uuid = job_dict.pop(Job.FIELD_JOB_UUID)
        column_list = list(job_dict.keys())
        value_list = list(job_dict.values()) + [job_uuid]
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=f"WHERE {Job.FIELD_JOB_UUID} = ?",
        )
        return self.get_job(job_in_db.job_uuid)

    def update_job_status(self, job_uuid: str, job_status: JobStatus) -> Job:
        where_clause = f"WHERE {Job.FIELD_JOB_UUID} = ?"
        value_list = [job_uuid]
        column_list = [Job.FIELD_JOB_STATUS, Job.FIELD_UPDATED_AT]
        value_list = [job_status, time_utils.current_datetime()] + value_list
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_job(job_uuid)

    def _reset_for_test(self) -> None:
        assert self.settings.DUCKDB_FILE == "duckdb_test.db"
        self.duckdb_client.delete_from_table(table_name=self.table_name)
