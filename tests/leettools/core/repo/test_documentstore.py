""" Tests for the DocumentStore class. """

from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.document import DocumentCreate, DocumentUpdate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org


def test_documentstore():

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
    docsource_store = repo_manager.get_docsource_store()
    docsink_store = repo_manager.get_docsink_store()
    doc_store = repo_manager.get_document_store()

    org_id = org.org_id
    kb_id = kb.kb_id

    # Test create_docsource
    docsource_create = DocSourceCreate(
        org_id=org_id,
        kb_id=kb_id,
        source_type=DocSourceType.URL,
        uri="http://www.test1.com",
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)
    docsource_uuid = docsource.docsource_uuid
    assert docsource_uuid is not None
    logger().info(f"Created docsource with UUID: {docsource_uuid}")

    docsink_create = DocSinkCreate(
        docsource=docsource,
        original_doc_uri="http://www.test1.com",
        raw_doc_uri="/tmp/test1.html",
    )
    docsink = docsink_store.create_docsink(org, kb, docsink_create)
    docsink_uuid = docsink.docsink_uuid
    assert docsink_uuid is not None
    logger().info(f"Created docsink with UUID: {docsink_uuid}")

    document_create = DocumentCreate(
        docsink=docsink,
        content="test content",
        doc_uri="uri1",
    )
    document = doc_store.create_document(org, kb, document_create)

    assert document.document_uuid is not None
    logger().info(f"Created document with UUID: {document.document_uuid}")

    # create the document again
    document2 = doc_store.create_document(org, kb, document_create)
    logger().info("Successfully created the document again.")
    assert document2 is not None
    assert document2.document_uuid != document.document_uuid

    # Test get_document
    document_uuid = document2.document_uuid
    document1 = doc_store.get_document_by_id(org, kb, document_uuid)
    assert document1 is not None
    assert document1.document_uuid == document_uuid
    logger().info(f"Retrieved document with UUID: {document1.document_uuid}")

    # Test update_document
    document_update = DocumentUpdate(
        document_uuid=document_uuid,
        doc_uri="uri2",
        content="updated content",
        docsink_uuid=docsink_uuid,
        docsource_uuids=[docsource_uuid],
        org_id=org_id,
        kb_id=kb_id,
    )
    document3 = doc_store.update_document(org, kb, document_update)
    assert document3 is not None and document3.content == document_update.content
    logger().info(f"Updated document with UUID: {document3.document_uuid}")

    # Test get_documents_for_kb
    documents = doc_store.get_documents_for_kb(org, kb)
    assert len(documents) == 1

    # Test get_documents_for_docsource
    documents = doc_store.get_documents_for_docsource(org, kb, docsource)
    assert len(documents) == 1

    # Test get_documents_for_docsink
    documents = doc_store.get_documents_for_docsink(org, kb, docsink)
    assert len(documents) == 1

    # Test delete_document
    result = doc_store.delete_document(org, kb, document3)
    assert result is True
    document = doc_store.get_document_by_id(org, kb, document_uuid)
    assert document is not None
    assert document.is_deleted is True
    logger().info(f"Deleted document with {document_uuid}")

    # Test get_documents_for_kb
    documents = doc_store.get_documents_for_kb(org, kb)
    assert len(documents) == 0

    # Test get_documents_for_docsource
    documents = doc_store.get_documents_for_docsource(org, kb, docsource)
    assert len(documents) == 0

    # Test get_documents_for_docsink
    documents = doc_store.get_documents_for_docsink(org, kb, docsink)
    assert len(documents) == 0

    docsource_store.delete_docsource(org, kb, docsource)
    docsink_store.delete_docsink(org, kb, docsink)
