from enum import Enum

from pydantic import BaseModel


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


def get_job_status_descriptions() -> list[JobStatusDescription]:
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
