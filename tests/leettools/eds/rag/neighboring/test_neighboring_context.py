from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SegmentCreate
from leettools.core.schemas.user import User
from leettools.eds.rag.context.neighboring_extension import NeighboringExtension


def test_segmentstore_neighbor_context():
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    ds = DocSource(
        org_id=org.org_id,
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
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test1",
        position_in_doc="1",
    )
    segment1 = segstore.create_segment(org, kb, segment_create)
    assert segment1 is not None

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test2",
        position_in_doc="1.1",
    )
    segment2 = segstore.create_segment(org, kb, segment_create)
    assert segment2 is not None

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test3",
        position_in_doc="1.2",
    )
    segment3 = segstore.create_segment(org, kb, segment_create)
    assert segment3 is not None

    segment_create = SegmentCreate(
        document_uuid=document_uuid,
        doc_uri=doc_uri,
        docsink_uuid=docsink_id,
        kb_id=kb_id,
        content="test4",
        position_in_doc="1.3",
    )
    segment4 = segstore.create_segment(org, kb, segment_create)
    assert segment4 is not None

    neighboring_context_mgr = NeighboringExtension(context)
    rtn_content = neighboring_context_mgr.get_neighboring_context(org, kb, segment3)
    assert rtn_content == "test1\n\ntest2\n\ntest3\n\ntest4\n\n"

    segments_set = set()
    segments_set.add(segment3.segment_uuid)
    segments_set.add(segment1.segment_uuid)
    segments_set.add(segment2.segment_uuid)
    rtn_content = neighboring_context_mgr.get_neighboring_context(
        org, kb, segment3, segments_set
    )
    assert rtn_content == "test3\n\ntest4\n\n"
    assert len(segments_set) == 4
