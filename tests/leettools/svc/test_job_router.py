from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.eds.scheduler.schemas.job import Job, JobCreate
from leettools.eds.scheduler.schemas.program import (
    ConnectorProgramSpec,
    ProgramSpec,
    ProgramType,
)
from leettools.eds.scheduler.schemas.task import TaskCreate
from leettools.svc.api.v1.routers.job_router import JobRouter


@pytest.mark.asyncio
async def test_stream_log_success():
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        task_manager = context.get_task_manager()
        task_store = task_manager.get_taskstore()

        docsource_store = context.get_repo_manager().get_docsource_store()
        docsource = docsource_store.create_docsource(
            org,
            kb,
            DocSourceCreate(
                org_id=org.org_id,
                kb_id=kb.kb_id,
                source_type=DocSourceType.LOCAL,
                uri="dummyuri",
                display_name="test doc source",
            ),
        )

        program_spec = ProgramSpec(
            program_type=ProgramType.CONNECTOR,
            real_program_spec=ConnectorProgramSpec(
                org_id=org.org_id, kb_id=kb.kb_id, source=docsource
            ),
        )

        task = task_store.create_task(
            TaskCreate(
                org_id=org.org_id,
                kb_id=kb.kb_id,
                docsource_uuid=docsource.docsource_uuid,
                program_spec=program_spec,
            )
        )

        job_store = task_manager.get_jobstore()
        job = job_store.create_job(
            JobCreate(task_uuid=task.task_uuid, program_spec=program_spec)
        )

        assert job.job_uuid is not None
        assert job.log_location is not None

        test_file_content = b"Hello, world!\nSecond line here."
        app = FastAPI(title="test")
        app.include_router(JobRouter())

        base_dir = Path(job.log_location).parent
        if not base_dir.exists():
            Path.mkdir(base_dir, parents=True)
        with open(job.log_location, "wb") as f:
            f.write(test_file_content)
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"/stream_logs/{job.job_uuid}")
            assert response.status_code == 200
            assert await response.aread() == test_file_content

            response = await ac.get(f"/logs/{job.job_uuid}")
            assert response.status_code == 200
            assert await response.aread() == test_file_content

            response = await ac.get(f"/fortask/{task.task_uuid}")
            assert response.status_code == 200
            assert len(response.json()) == 1
            retrieved_job = Job.model_validate(response.json()[0])
            assert retrieved_job.job_uuid == job.job_uuid
            assert retrieved_job.task_uuid == job.task_uuid
            assert retrieved_job.log_location == job.log_location

            response = await ac.get(f"/{job.job_uuid}")
            assert response.status_code == 200
            retrieved_job = Job.model_validate(response.json())
            assert retrieved_job.job_uuid == job.job_uuid
            assert retrieved_job.task_uuid == job.task_uuid
            assert retrieved_job.log_location == job.log_location
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


@pytest.mark.asyncio
async def test_stream_log_file_not_found():
    app = FastAPI(title="test")
    app.include_router(JobRouter())
    async with AsyncClient(app=app, base_url="http://test") as ac:
        job_uuid = "73727787-6914-4fc6-ab5d-13df949840ab"
        response = await ac.get(f"/logs/{job_uuid}")
        assert response.status_code == 404
        assert response.json() == {"detail": f"Job {job_uuid} not found."}
