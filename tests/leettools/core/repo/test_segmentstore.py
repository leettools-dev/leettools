from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SegmentCreate, SegmentUpdate
from leettools.core.schemas.user import User


def test_segmentstore():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        ds = DocSource(
            kb_id=kb.kb_id,
            uri="doc_source_uri_001",
            docsource_uuid="doc_source_uuid_001",
            source_type=DocSourceType.FILE,
        )

        try:
            _test_function(context, org, kb, user, ds)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb, user)
            repo_manager = context.get_repo_manager()
            segstore = repo_manager.get_segment_store()
            for segment in segstore.get_segments_for_docsource(org, kb, ds):
                segstore.delete_segment(org, kb, segment)


def _test_function(
    context: Context, org: Org, kb: KnowledgeBase, user: User, ds: DocSource
):

    repo_manager = context.get_repo_manager()
    segstore = repo_manager.get_segment_store()

    kb_id = kb.kb_id

    docsource_id = ds.docsource_uuid

    document_uuid = "doc1"
    doc_uri = "uri1"
    docsink_id = "sink1"
    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsource_uuid=docsource_id,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test content",
        position_in_doc="1",
    )
    segment = segstore.create_segment(org, kb, segment_create)
    assert segment.segment_uuid is not None
    logger().info(f"Created segment with SEGMENT_UUID: {segment.segment_uuid}")

    # Test get_segment
    doc_id = segment.document_uuid
    position_doc = segment.position_in_doc
    segment = segstore.get_segment(org, kb, doc_id, position_doc)
    assert segment is not None
    logger().info(f"Retrieved segment with SEGMENT_UUID: {segment.segment_uuid}")

    # Test get_segment_by_uuid
    segment10 = segstore.get_segment_by_uuid(org, kb, segment.segment_uuid)
    assert segment10.segment_uuid == segment.segment_uuid
    assert segment10.content == segment.content

    # Test update_segment
    segment_update = SegmentUpdate(
        segment_uuid=segment.segment_uuid,
        document_uuid=segment.document_uuid,
        doc_uri=segment.doc_uri,
        docsource_uuid=docsource_id,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="updated content",  # changed content
        position_in_doc="1",
    )
    segment = segstore.update_segment(org, kb, segment_update)
    assert segment is not None and segment.content == segment_update.content
    logger().info(f"Updated segment with SEGMENT_UUID: {segment.segment_uuid}")

    # Test delete_segment
    doc_id = segment.document_uuid
    position_doc = segment.position_in_doc
    result = segstore.delete_segment(org, kb, segment)
    assert result is True
    segment = segstore.get_segment(org, kb, doc_id, position_doc)
    assert segment is None
    logger().info(f"Deleted segment with {doc_id} and {position_doc}")

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsource_uuid=docsource_id,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test content",
        position_in_doc="1",
    )
    segment = segstore.create_segment(org, kb, segment_create)
    assert segment.segment_uuid is not None

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsource_uuid=docsource_id,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test content",
        position_in_doc="1.0",
    )
    segment10 = segstore.create_segment(org, kb, segment_create)
    assert segment10 is not None

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsource_uuid=docsource_id,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test content",
        position_in_doc="1.1",
    )
    segment11 = segstore.create_segment(org, kb, segment_create)
    assert segment11 is not None

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsource_uuid=docsource_id,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test content",
        position_in_doc="1.2",
    )
    segment12 = segstore.create_segment(org, kb, segment_create)
    assert segment12 is not None

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsource_uuid=docsource_id,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test content",
        position_in_doc="1.3",
    )
    segment13 = segstore.create_segment(org, kb, segment_create)
    assert segment13 is not None

    parent_segment = segstore.get_parent_segment(org, kb, segment11)
    assert parent_segment is not None
    assert parent_segment.position_in_doc == "1"
    assert parent_segment.document_uuid == document_uuid
    assert parent_segment.segment_uuid == segment.segment_uuid

    older_segment = segstore.get_older_sibling_segment(org, kb, segment10)
    assert older_segment is None
    younger_segment = segstore.get_younger_sibling_segment(org, kb, segment11)
    assert younger_segment is not None
    assert younger_segment.position_in_doc == "1.2"
    assert younger_segment.document_uuid == document_uuid
    assert younger_segment.segment_uuid == segment12.segment_uuid

    parent_segment = segstore.get_parent_segment(org, kb, segment12)
    assert parent_segment is not None
    assert parent_segment.position_in_doc == "1"
    assert parent_segment.document_uuid == document_uuid
    assert parent_segment.segment_uuid == segment.segment_uuid

    older_segment = segstore.get_older_sibling_segment(org, kb, segment12)
    assert older_segment is not None
    assert older_segment.position_in_doc == "1.1"
    assert older_segment.document_uuid == document_uuid
    assert older_segment.segment_uuid == segment11.segment_uuid
    younger_segment = segstore.get_younger_sibling_segment(org, kb, segment12)
    assert younger_segment is not None
    assert younger_segment.position_in_doc == "1.3"
    assert younger_segment.document_uuid == document_uuid
    assert younger_segment.segment_uuid == segment13.segment_uuid

    older_segment = segstore.get_older_sibling_segment(org, kb, segment13)
    assert older_segment is not None
    assert older_segment.position_in_doc == "1.2"
    assert older_segment.document_uuid == document_uuid
    assert older_segment.segment_uuid == segment12.segment_uuid
    younger_segment = segstore.get_younger_sibling_segment(org, kb, segment13)
    assert younger_segment is None
