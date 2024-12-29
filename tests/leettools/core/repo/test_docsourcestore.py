from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import (
    DocSourceCreate,
    DocSourceUpdate,
    IngestConfig,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org


def test_docsourcestore():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    repo_manager = context.get_repo_manager()
    dsstore = repo_manager.get_docsource_store()
    kb_id = kb.kb_id

    # Test create_docsource
    # uri is a HttpUrl in pydantic
    docsource_create = DocSourceCreate(
        source_type=DocSourceType.URL,
        uri="http://www.test1.com/",
        kb_id=kb_id,
    )
    docsource1 = dsstore.create_docsource(org, kb, docsource_create)
    assert docsource1.docsource_uuid is not None
    logger().info(f"Created docsource with UUID: {docsource1.docsource_uuid}")

    docsource_create2 = DocSourceCreate(
        source_type=DocSourceType.NOTION,
        uri="http://www.test2.com",
        kb_id=kb_id,
        ingest_config=IngestConfig(
            flow_options={}, extra_parameters={"access_token": "test"}
        ),
    )
    docsource2 = dsstore.create_docsource(org, kb, docsource_create2)
    assert docsource2 is not None
    assert docsource2.docsource_uuid is not None
    logger().info(f"Created docsource with UUID: {docsource2.docsource_uuid}")

    # Test update_docsource
    docsource_update = DocSourceUpdate(
        docsource_uuid=docsource1.docsource_uuid,
        source_type=docsource1.source_type,
        uri="http://www.example.com",
        kb_id=kb_id,
        docsource_status=DocSourceStatus.COMPLETED,
    )
    docsource3 = dsstore.update_docsource(org, kb, docsource_update)
    assert docsource3 is not None
    logger().info(f"Updated docsource with UUID: {docsource3.docsource_uuid}")

    # Test get_docsource
    docsource4 = dsstore.get_docsource(org, kb, docsource1.docsource_uuid)
    assert docsource4 is not None
    assert docsource4.uri == "http://www.example.com"
    logger().info(f"Retrieved docsource with UUID: {docsource4.docsource_uuid}")

    # Test get_docsources_for_kb
    docsources = dsstore.get_docsources_for_kb(org, kb)
    assert len(docsources) == 2
    logger().info(f"Retrieved {len(docsources)} docsources")

    # Test delete_docsource
    result = dsstore.delete_docsource(org, kb, docsource1)
    assert result is True
    docsource5 = dsstore.get_docsource(org, kb, docsource1.docsource_uuid)
    assert docsource5 is not None
    assert docsource5.is_deleted is True
    logger().info(f"Deleted docsource with {docsource1.docsource_uuid}")

    docsources = dsstore.get_docsources_for_kb(org, kb)
    assert len(docsources) == 1

    retriever_type = "google"
    query = "test"
    days_limit = 0
    max_results = 10
    timestamp = "2022-01-01-00-00-00"
    flow_options = {
        "retriever_type": retriever_type,
        "days_limit": days_limit,
        "max_results": max_results,
    }

    docsource_create = DocSourceCreate(
        kb_id=kb_id,
        source_type=DocSourceType.SEARCH,
        uri=(
            f"search://{retriever_type}?q={query}&date_range={days_limit}"
            f"&max_results={max_results}&ts={timestamp}"
        ),
        display_name=query,
        ingest_config=IngestConfig(
            flow_options=flow_options,
        ),
    )

    docsource_3 = dsstore.create_docsource(org, kb, docsource_create)
    assert docsource_3 is not None
    assert docsource_3.kb_id == kb_id
    assert docsource_3.source_type == DocSourceType.SEARCH
    assert docsource_3.uri == (
        f"search://{retriever_type}?q={query}&date_range={days_limit}"
        f"&max_results={max_results}&ts={timestamp}"
    )
    assert docsource_3.display_name == query
    assert isinstance(docsource_3.ingest_config, IngestConfig)
