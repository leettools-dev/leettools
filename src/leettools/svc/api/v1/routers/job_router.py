from typing import List, Optional

import aiofiles
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from leettools.eds.scheduler.schemas.job import Job
from leettools.eds.scheduler.schemas.job_status import (
    JobStatusDescription,
    get_job_status_descriptions,
)
from leettools.svc.api_router_base import APIRouterBase


class JobRouter(APIRouterBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        task_manager = context.get_task_manager()
        self.task_store = task_manager.get_taskstore()
        self.job_store = task_manager.get_jobstore()

        @self.get("/status_types", response_model=List[JobStatusDescription])
        async def get_job_status_types():
            """
            Get all job statuses
            """
            return get_job_status_descriptions()

        @self.get("/fortask/{task_uuid}", response_model=List[Job])
        async def get_jobs_for_task(task_uuid: str) -> List[Job]:
            """
            Get all jobs for a task
            """
            jobs = self.job_store.get_all_jobs_for_task(task_uuid)
            return jobs

        async def read_log_file(file_path: str):
            async with aiofiles.open(file_path, mode="rb") as file:
                while True:
                    chunk = await file.read(4096)  # Read in chunks of 4KB
                    if not chunk:
                        break
                    yield chunk

        @self.get("/stream_logs/{job_uuid}")
        async def stream_log(job_uuid: str) -> StreamingResponse:
            job = self.job_store.get_job(job_uuid)
            if job is None:
                raise HTTPException(
                    status_code=404, detail=f"Job {job_uuid} not found."
                )
            log_path = job.log_location
            try:
                return StreamingResponse(
                    read_log_file(log_path), media_type="text/plain"
                )
            except FileNotFoundError:
                raise HTTPException(
                    status_code=404, detail=f"Log file {log_path} not found."
                )

        @self.get("/logs/{job_uuid}", response_class=PlainTextResponse)
        async def read_log(job_uuid: str):
            job = self.job_store.get_job(job_uuid)
            if job is None:
                raise HTTPException(
                    status_code=404, detail=f"Job {job_uuid} not found."
                )
            log_path = job.log_location
            try:
                with open(log_path, "r") as file:
                    return file.read()
            except FileNotFoundError:
                raise HTTPException(
                    status_code=404, detail="Log file {log_path} not found."
                )

        @self.get("/{job_uuid}", response_model=Optional[Job])
        async def get_job(job_uuid: str) -> Job:
            job = self.job_store.get_job(job_uuid)
            return job
