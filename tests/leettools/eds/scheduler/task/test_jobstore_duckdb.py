""" Test the jobstore """

from time import sleep

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSource, DocSourceCreate, DocSourceInDB
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.schemas.job import JobCreate
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.eds.scheduler.schemas.program import (
    ConnectorProgramSpec,
    ProgramSpec,
    ProgramType,
)
from leettools.eds.scheduler.schemas.task import TaskCreate
from leettools.eds.scheduler.task._impl.duckdb.jobstore_duckdb import JobStoreDuckDB
from leettools.eds.scheduler.task._impl.duckdb.taskstore_duckdb import TaskStoreDuckDB


def test_jobstore():
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_function(context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    kb_id = kb.kb_id

    settings = context.settings
    settings.DUCKDB_FILE = "duckdb_test.db"
    taskstore = TaskStoreDuckDB(settings)
    jobstore = JobStoreDuckDB(settings)
    taskstore._reset_for_test()
    jobstore._reset_for_test()

    # create docsource
    doc_source_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        source_type=DocSourceType.URL,
        uri="https://www.examples.com/",
    )
    docsource_uuid = "123456"
    docsource_in_db = DocSourceInDB.from_docsource_create(doc_source_create)
    docsource_in_db.docsource_uuid = docsource_uuid
    docsource = DocSource.from_docsource_in_db(docsource_in_db)

    # create a task
    real_spec = ConnectorProgramSpec(
        org_id=org.org_id, kb_id=kb.kb_id, source=docsource
    )
    program_spec = ProgramSpec(
        program_type=ProgramType.CONNECTOR, real_program_spec=real_spec
    )
    task_create = TaskCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        docsource_uuid=docsource_uuid,
        program_spec=program_spec,
    )
    task = taskstore.create_task(task_create)
    assert task is not None
    assert task.created_at is not None

    # create a job
    job_create = JobCreate(task_uuid=task.task_uuid, program_spec=program_spec)
    job = jobstore.create_job(job_create)
    assert job is not None
    assert job.job_uuid is not None
    assert job.created_at is not None
    assert job.log_location is not None

    # get the job
    job1 = jobstore.get_job(job.job_uuid)
    assert job1 is not None
    assert job.job_uuid is not None
    assert job.created_at is not None
    assert job.log_location is not None
    assert job.job_status == JobStatus.PENDING

    # get jobs
    jobs = jobstore.get_all_jobs_for_task(task.task_uuid)
    assert jobs is not None
    assert len(jobs) == 1

    # create another job
    sleep(2)
    job_create = JobCreate(task_uuid=task.task_uuid, program_spec=program_spec)
    job2 = jobstore.create_job(job_create)
    assert job2 is not None
    assert job2.created_at is not None

    jobs = jobstore.get_all_jobs_for_task(task.task_uuid)
    assert jobs is not None
    assert len(jobs) == 2

    # get the latest job
    latest_job = jobstore.get_the_latest_job_for_task(task.task_uuid)
    assert latest_job is not None
    assert latest_job.job_uuid == job2.job_uuid

    # update the job
    sleep(2)
    job_update = job.model_copy()
    job_update.job_status = JobStatus.RUNNING
    job_update.progress = 0.5

    job3 = jobstore.update_job(job_update)
    assert job3 is not None
    assert job3.job_uuid == job.job_uuid
    assert job3.updated_at != job.updated_at
    assert job3.job_status == JobStatus.RUNNING
    assert job.job_status == JobStatus.PENDING

    assert job3.progress == 0.5

    # get the latest job again
    latest_job = jobstore.get_the_latest_job_for_task(task.task_uuid)
    assert latest_job is not None
    assert latest_job.job_uuid == job.job_uuid

    # delete the job
    rtn_value = jobstore.delete_job(job.job_uuid)
    assert rtn_value == True
    job4 = jobstore.get_job(job.job_uuid)
    assert job4.is_deleted == True

    jobs = jobstore.get_all_jobs_for_task(task.task_uuid)
    assert len(jobs) == 1
