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

    filepath = Path.joinpath(tmp_path, "test.md")
    with open(filepath, "w") as f:
        f.write(
            "#Title with a head\n"
            "Paragraph 1 as 1\n"
            "Paragraph 2 as 1\n"
            "Paragraph 3 as 3\n"
        )

    # create docsource
    doc_source_create = DocSourceCreate(
        source_type=DocSourceType.LOCAL,
        uri=filepath.absolute().as_uri(),
        kb_id=kb_id,
    )
    docsource_store.create_docsource(org, kb, doc_source_create)

    logger().info("Added a new docsource.")
    # now the scheduler should pick up the task and run it
    run_scheduler(context)
    logger().info("Finished running the task.")
