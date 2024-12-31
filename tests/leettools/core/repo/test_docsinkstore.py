from pathlib import Path

from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.common.utils.file_utils import file_hash_and_size
from leettools.context_manager import Context
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsink import DocSinkCreate, DocSinkUpdate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org


def test_docsinkstore(tmp_path):

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        logger().info(
            f"Testing with doc_store: {context.settings.DOC_STORE_TYPE} "
            f"and vector_store: {context.settings.VECTOR_STORE_TYPE}"
        )

        try:
            _test_function(tmp_path, context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)
            logger().info(
                f"Finished testing doc_store: {context.settings.DOC_STORE_TYPE} "
                f"and vector_store: {context.settings.VECTOR_STORE_TYPE}"
            )


def _test_function(tmp_path, context: Context, org: Org, kb: KnowledgeBase):

    repo_manager = context.get_repo_manager()

    docsource_store = repo_manager.get_docsource_store()
    docsink_store = repo_manager.get_docsink_store()
    kb_id = kb.kb_id

    # Create a DocSource for test
    docsource_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb_id,
        source_type=DocSourceType.URL,
        uri="http://www.test1.com",
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)
    docsource_uuid = docsource.docsource_uuid
    assert docsource_uuid is not None
    logger().info(f"Created docsource with UUID: {docsource_uuid}")

    # Test create_docsink
    raw_doc_uri = Path(tmp_path / "data" / "www-test1-com" / "index.html")
    raw_doc_uri.parent.mkdir(parents=True, exist_ok=True)
    raw_doc_uri.write_text("test")
    doc_hash_1, doc_size = file_hash_and_size(Path(raw_doc_uri))
    docsink_create = DocSinkCreate(
        docsource=docsource,
        original_doc_uri="http://www.test1.com",
        raw_doc_uri=str(raw_doc_uri),
        raw_doc_hash=doc_hash_1,
        size=doc_size,
    )
    docsink1 = docsink_store.create_docsink(org, kb, docsink_create)
    assert docsink1 is not None
    assert docsink1.docsink_uuid is not None
    assert docsink1.docsource_uuids == [docsource_uuid]
    assert docsink1.docsink_status == DocSinkStatus.CREATED
    assert docsink1.is_deleted is False
    assert docsink1.expired_at is None
    logger().info(f"Created docsink with UUID: {docsink1.docsink_uuid}")

    # Create another DocSink with the same hash
    # Since the URI is different, it should create a new DocSink
    raw_doc_uri = Path(tmp_path / "data" / "www-test2-com" / "index.html")
    raw_doc_uri.parent.mkdir(parents=True, exist_ok=True)
    raw_doc_uri.write_text("test")
    doc_hash_2, doc_size = file_hash_and_size(Path(raw_doc_uri))
    docsink_create = DocSinkCreate(
        docsource=docsource,
        original_doc_uri="http://www.test2.com",
        raw_doc_uri=str(raw_doc_uri),
        raw_doc_hash=doc_hash_2,
        size=doc_size,
    )
    assert doc_hash_1 == doc_hash_2
    docsink2 = docsink_store.create_docsink(org, kb, docsink_create)
    assert docsink2.docsink_uuid is not None
    assert docsink2.docsink_uuid != docsink1.docsink_uuid
    assert docsink2.docsource_uuids == docsink1.docsource_uuids

    # docsink1 should be still the same
    docsink1_retrieved = docsink_store.get_docsink_by_id(org, kb, docsink1.docsink_uuid)
    assert docsink1_retrieved is not None
    assert docsink1_retrieved.docsink_uuid == docsink1.docsink_uuid
    assert docsink1_retrieved.docsink_status == DocSinkStatus.CREATED
    assert docsink1_retrieved.is_deleted is False
    assert docsink1_retrieved.expired_at is None

    # create another DocSink with different hash and URI
    raw_doc_uri = Path(tmp_path / "data" / "www-test3-com" / "index.html")
    raw_doc_uri.parent.mkdir(parents=True, exist_ok=True)
    raw_doc_uri.write_text("test3")
    doc_hash_3, doc_size = file_hash_and_size(Path(raw_doc_uri))
    docsink_create = DocSinkCreate(
        docsource=docsource,
        original_doc_uri="http://www.test3.com/with-'-and-$-and-@",
        raw_doc_uri=str(raw_doc_uri),
        raw_doc_hash=doc_hash_3,
        size=doc_size,
    )
    assert doc_hash_1 != doc_hash_3
    docsink3 = docsink_store.create_docsink(org, kb, docsink_create)
    assert docsink3.docsink_uuid is not None
    assert docsink3.docsink_uuid != docsink1.docsink_uuid

    # We should have three DocSinks for the DocSource now
    docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)
    assert len(docsinks) == 3

    # Test update_docsink
    docsink_update = DocSinkUpdate(
        docsink_uuid=docsink1.docsink_uuid,
        docsource_uuids=[docsource_uuid],
        org_id=org.org_id,
        kb_id=kb_id,
        original_doc_uri="http://www.example.com/",
        raw_doc_uri=str(raw_doc_uri),
    )
    docsink4 = docsink_store.update_docsink(org, kb, docsink_update)
    assert docsink4 is not None
    logger().info(f"Updated docsink with UUID: {docsink4.docsink_uuid}")

    # Test get_docsink_by_id
    docsink5 = docsink_store.get_docsink_by_id(org, kb, docsink1.docsink_uuid)
    assert docsink5 is not None
    assert str(docsink5.original_doc_uri) == "http://www.example.com/"
    logger().info(f"Retrieved docsink with UUID: {docsink5.docsink_uuid}")

    # Test get_docsink_for_kb
    docsinks = docsink_store.get_docsinks_for_kb(org, kb)
    assert len(docsinks) == 3

    # Test get_docsinks_for_docsource
    docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)
    assert len(docsinks) == 3

    # Test delete_docsink
    result = docsink_store.delete_docsink(org, kb, docsink1)
    assert result is True
    docsink5 = docsink_store.get_docsink_by_id(org, kb, docsink1.docsink_uuid)
    assert docsink5 is not None
    assert docsink5.is_deleted is True
    logger().info(f"Deleted docsink with {docsink1.docsink_uuid}")

    # Test get_docsink_for_kb
    docsinks = docsink_store.get_docsinks_for_kb(org, kb)
    assert len(docsinks) == 2

    # Test get_docsinks_for_docsource
    docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)
    assert len(docsinks) == 2

    docsink_store.delete_docsink(org, kb, docsink4)
    docsource_store.delete_docsource(org, kb, docsource)
