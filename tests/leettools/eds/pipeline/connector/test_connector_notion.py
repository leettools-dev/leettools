import os

import pytest

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate, IngestConfig
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.pipeline.ingest.connector import create_connector


def test_connector_notion():
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_function(context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    settings = context.settings
    kb_id = kb.kb_id

    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()
    docsink_store = repo_manager.get_docsink_store()

    kb_id = settings.DEFAULT_KNOWLEDGEBASE_NAME
    access_token = os.getenv("NOTION_ACCESS_TOKEN", default="dummytoken")

    docsource_create = DocSourceCreate(
        source_type=DocSourceType.NOTION,
        uri="https://www.notion.so/ca3b53e7585a4114bc1f00cf03795a3d?v=e1c179b7096e4c2bb936b62f62dcbff5",
        kb_id=kb_id,
        ingest_config=IngestConfig(
            flow_options={}, extra_parameters={"access_token": access_token}
        ),
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)
    connector = create_connector(
        context, "connector_notion", org, kb, docsource, docsink_store
    )

    # Note: You have to setup a notion access token to run the following test
    # return_code = connector.ingest()
    # assert return_code == ReturnCode.SUCCESS
    # docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)
    # assert len(docsinks) > 0
    # logger().info(f"Saved {len(docsinks)} docsinks!")


if __name__ == "__main__":
    pytest.main()
