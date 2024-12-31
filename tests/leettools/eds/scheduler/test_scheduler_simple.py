from pathlib import Path

from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.scheduler_manager import run_scheduler


# TODO: make task_scanner take org / kb as a parameter
def test_simple_scheduler(tmp_path) -> None:
    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_function(tmp_path, temp_setup.context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(tmp_path, context: Context, org: Org, kb: KnowledgeBase):

    kb_id = kb.kb_id

    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()

    task_manager = context.get_task_manager()
    taskstore = task_manager.get_taskstore()
    taskstore._reset_for_test()
    jobstore = task_manager.get_jobstore()
    jobstore._reset_for_test()

    logger().info("Adding a new docsource.")

    filepath_01 = Path.joinpath(tmp_path, "test_01.md")
    with open(filepath_01, "w") as f:
        f.write(
            "#Title with a head\n"
            "Paragraph 1 as 1\n"
            "Paragraph 2 as 1\n"
            "Paragraph 3 as 3\n"
        )

    # create docsource
    doc_source_create_01 = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        source_type=DocSourceType.LOCAL,
        uri=filepath_01.absolute().as_uri(),
    )
    docsource_01 = docsource_store.create_docsource(org, kb, doc_source_create_01)

    logger().info("Added a new docsource.")
    # now the scheduler should pick up the task and run it
    run_scheduler(context)
    logger().info("Finished running the task for kb.")

    filepath_02 = Path.joinpath(tmp_path, "test_01.md")
    with open(filepath_02, "w") as f:
        f.write(
            "#Title with a head\n"
            "Paragraph 1 as 1\n"
            "Paragraph 2 as 1\n"
            "Paragraph 3 as 3\n"
        )

    doc_source_create_02 = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        source_type=DocSourceType.LOCAL,
        uri=filepath_02.absolute().as_uri(),
    )
    docsource_02 = docsource_store.create_docsource(org, kb, doc_source_create_02)
    run_scheduler(context, org=org, kb=kb, docsources=[docsource_02])

    logger().info("Finished running the task for docsource 02.")
