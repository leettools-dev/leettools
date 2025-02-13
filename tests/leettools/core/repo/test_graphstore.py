from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SegmentInDB


def test_graphstore():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]
        context.settings.GRAPH_STORE_TYPE = store_types["graph_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    repo_manager = context.get_repo_manager()
    graphstore = repo_manager.get_docgraph_store()
    kb_id = kb.kb_id

    segment1_in_store = SegmentInDB(
        segment_uuid="1",
        document_uuid="doc1",
        doc_uri="uri1",
        docsink_uuid="docsink1",
        kb_id=kb_id,
        content="test content1",
        position_in_doc="test position1",
        heading="test heading1",
        start_offset=0,
        end_offset=10,
    )

    node_id1 = graphstore.create_segment_node(segment1_in_store)
    logger().info(
        f"Created segment {segment1_in_store.segment_uuid} with node_id: {node_id1}"
    )
    assert node_id1 is not None

    segment2_in_store = SegmentInDB(
        segment_uuid="2",
        document_uuid="doc2",
        doc_uri="uri2",
        docsink_uuid="docsink1",
        kb_id=kb_id,
        content="test content2",
        position_in_doc="test position2",
        heading="test heading2",
        start_offset=0,
        end_offset=10,
    )

    node_id2 = graphstore.create_segment_node(segment2_in_store)
    logger().info(
        f"Created segment {segment2_in_store.segment_uuid} with node_id: {node_id2}"
    )
    assert node_id2 is not None

    # Test create_segments_relationship
    relationship_id = graphstore.create_segments_relationship(node_id1, node_id2)
    logger().info(f"Created relationship with id: {relationship_id}")
    assert relationship_id is not None

    # Test update_segment_node
    segment1_in_store.heading = "updated heading1"
    node1_id = graphstore.update_segment_node(segment1_in_store)
    logger().info(
        f"Updated segment {segment1_in_store.segment_uuid} with node_id: {node1_id}"
    )
    assert node1_id is not None

    segment2_in_store.heading = "updated heading2"
    node2_id = graphstore.update_segment_node(segment2_in_store)
    logger().info(
        f"Updated segment {segment2_in_store.segment_uuid} with node_id: {node2_id}"
    )
    assert node2_id is not None

    # Test delete_segments_relationship
    result = graphstore.delete_segments_relationship(node_id1, node_id2)
    logger().info(f"Deleted relationship with id: {relationship_id}")
    assert result is True

    # Test delete_segment_node
    result = graphstore.delete_segment_node(segment1_in_store)
    logger().info(f"Deleted node for segment {segment1_in_store.segment_uuid}")
    assert result is True

    result = graphstore.delete_segment_node(segment2_in_store)
    logger().info(f"Deleted node for segment {segment2_in_store.segment_uuid}")
    assert result is True
