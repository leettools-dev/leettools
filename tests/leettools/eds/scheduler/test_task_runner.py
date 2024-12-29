import pytest

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSource, DocSourceCreate, DocSourceInDB
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.scheduler._impl.task_runner_eds import TaskRunnerEDS
from leettools.eds.scheduler.schemas.job import JobCreate
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.eds.scheduler.schemas.program import (
    ConnectorProgramSpec,
    ConvertProgramSpec,
    EmbedProgramSpec,
    ProgramSpec,
    ProgramType,
    SplitProgramSpec,
)


def test_task_runner():
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_function(context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb, user)


def _test_function(context: Context, org: Org, kb: KnowledgeBase, user: User):
    kb_id = kb.kb_id

    task_runner = TaskRunnerEDS(context)

    jobstore = task_runner.jobstore
    docstore = task_runner.docstore
    segstore = task_runner.segstore

    original_test_uri = "https://en.linktimecloud.com/"

    # create docsource
    doc_source_create = DocSourceCreate(
        source_type=DocSourceType.URL,
        uri=original_test_uri,
        kb_id=kb_id,
    )
    docsource_uuid = "123456"
    docsource_in_db = DocSourceInDB.from_docsource_create(doc_source_create)
    docsource_in_db.docsource_uuid = docsource_uuid
    docsource = DocSource.from_docsource_in_db(docsource_in_db)

    # create a ingest task
    real_spec = ConnectorProgramSpec(org_id=org.org_id, kb_id=kb_id, source=docsource)
    program_spec = ProgramSpec(
        program_type=ProgramType.CONNECTOR,
        docsource_uuid=docsource_uuid,
        real_program_spec=real_spec,
    )

    ingeat_task_uuid = "ingest_task_uuid"
    job_create = JobCreate(task_uuid=ingeat_task_uuid, program_spec=program_spec)
    job = jobstore.create_job(job_create)

    # run the task
    job = task_runner.run_job(job)
    assert job.job_status == JobStatus.COMPLETED

    # create a convert task
    docsink_store = task_runner.docsinkstore
    docsink = docsink_store.get_docsinks_for_docsource(org, kb, docsource)[0]
    real_spec = ConvertProgramSpec(org_id=org.org_id, kb_id=kb_id, source=docsink)
    program_spec = ProgramSpec(
        program_type=ProgramType.CONVERT, real_program_spec=real_spec
    )
    convert_task_uuid = "convert_task_uuid"
    job_create = JobCreate(task_uuid=convert_task_uuid, program_spec=program_spec)
    job = jobstore.create_job(job_create)

    # run the task
    job = task_runner.run_job(job)
    assert job.job_status == JobStatus.COMPLETED

    # create a split task
    docstore = task_runner.docstore
    doc = docstore.get_documents_for_docsource(org, kb, docsource)[0]
    real_spec = SplitProgramSpec(
        org_id=org.org_id,
        kb_id=kb_id,
        source=doc,
    )
    program_spec = ProgramSpec(
        program_type=ProgramType.SPLIT, real_program_spec=real_spec
    )
    split_task_uuid = "split_task_uuid"
    job_create = JobCreate(task_uuid=split_task_uuid, program_spec=program_spec)
    job = jobstore.create_job(job_create)

    # run the task
    job = task_runner.run_job(job)
    assert job.job_status == JobStatus.COMPLETED

    # create a embed task
    segment = segstore.get_segments_for_docsource(org, kb, docsource)[0]
    real_spec = EmbedProgramSpec(org_id=org.org_id, kb_id=kb_id, source=[segment])
    program_spec = ProgramSpec(
        program_type=ProgramType.EMBED, real_program_spec=real_spec
    )
    embed_task_uuid = "embed_task_uuid"
    job_create = JobCreate(task_uuid=embed_task_uuid, program_spec=program_spec)
    job = jobstore.create_job(job_create)

    assert segment.original_uri == original_test_uri
    # run the task
    job = task_runner.run_job(job)
    assert job.job_status == JobStatus.COMPLETED


if __name__ == "__main__":
    pytest.main()
