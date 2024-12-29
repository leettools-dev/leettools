from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsink import DocSink, DocSinkCreate
from leettools.core.schemas.docsource import DocSource, DocSourceCreate, DocSourceInDB
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.eds.scheduler.schemas.program import (
    ConnectorProgramSpec,
    ConvertProgramSpec,
    ProgramSpec,
    ProgramType,
)
from leettools.eds.scheduler.schemas.task import TaskCreate
from leettools.eds.scheduler.task._impl.duckdb.taskstore_duckdb import TaskStoreDuckDB


def test_taskstore_duckdb():
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
    taskstore._reset_for_test()

    # create docsource
    doc_source_create = DocSourceCreate(
        source_type=DocSourceType.URL,
        uri="https://www.examples.com/",
        kb_id=kb_id,
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
        kb_id=kb_id,
        docsource_uuid=docsource_uuid,
        program_spec=program_spec,
    )
    task_1 = taskstore.create_task(task_create)
    assert task_1 is not None
    assert task_1.docsource_uuid == docsource_uuid
    assert task_1.task_uuid is not None
    assert task_1.created_at is not None

    # create another task
    docsink = DocSink.from_docsink_create(
        DocSinkCreate(
            docsource_uuid=docsource_uuid,
            kb_id=kb_id,
            original_doc_uri="https://www.examples.com/",
            raw_doc_uri="/tmp/www_examples_com",
        )
    )
    real_spec = ConvertProgramSpec(org_id=org.org_id, kb_id=kb.kb_id, source=docsink)
    program_spec = ProgramSpec(
        program_type=ProgramType.CONVERT, real_program_spec=real_spec
    )
    task_create = TaskCreate(
        org_id=org.org_id,
        kb_id=kb_id,
        docsource_uuid=docsource_uuid,
        docsink_uuid="123456",
        program_spec=program_spec,
    )
    task_2 = taskstore.create_task(task_create)
    assert task_2 is not None

    # get the task
    task_2_retrieved = taskstore.get_task_by_uuid(task_2.task_uuid)
    assert task_2_retrieved is not None
    assert task_2_retrieved.task_uuid == task_2.task_uuid
    assert task_2_retrieved.docsource_uuid == docsource_uuid
    assert task_2_retrieved.created_at is not None

    # get tasks
    tasks = taskstore.get_tasks_for_docsource(docsource_uuid)
    assert tasks is not None
    assert len(tasks) == 2

    # get all tasks
    tasks = taskstore.get_all_tasks()
    assert tasks is not None
    assert len(tasks) == 2

    # get incomplete tasks
    tasks = taskstore.get_incomplete_tasks()
    assert tasks is not None
    assert len(tasks) == 2

    # update the task
    task_update = task_2.model_copy()
    task2_updated = taskstore.update_task(task_update)
    assert task2_updated is not None
    assert task2_updated.docsource_uuid == docsource_uuid
    assert task2_updated.task_uuid == task_2.task_uuid
    assert task2_updated.program_spec == task_2.program_spec
    assert task2_updated.updated_at is not None

    # update the task status
    taskstore.update_task_status(task_2.task_uuid, JobStatus.COMPLETED)

    # get incomplete tasks
    tasks = taskstore.get_incomplete_tasks()
    assert tasks is not None
    assert len(tasks) == 1

    # delete the task
    success = taskstore.delete_task(task_2.task_uuid)
    assert success == True

    task2_deleted = taskstore.get_task_by_uuid(task_2.task_uuid)
    assert task2_deleted is not None
    assert task2_deleted.is_deleted == True
