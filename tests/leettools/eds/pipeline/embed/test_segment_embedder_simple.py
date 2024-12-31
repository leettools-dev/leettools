from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.return_code import ReturnCode
from leettools.core.consts.segment_embedder_type import SegmentEmbedderType
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SegmentCreate
from leettools.core.schemas.user import User
from leettools.eds.pipeline.embed.segment_embedder import create_segment_embedder_for_kb


def test_segement_embedder_simple():
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    context.settings.DEFAULT_SEGMENT_EMBEDDER_TYPE = SegmentEmbedderType.SIMPLE
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
        content="test content",
        position_in_doc="1",
    )
    segment = segstore.create_segment(org, kb, segment_create)
    assert segment.segment_uuid is not None

    embedder = create_segment_embedder_for_kb(org, kb, user, context)
    assert embedder.embed_segment_list([segment]) == ReturnCode.SUCCESS
    assert (
        embedder.dense_vectorstore.get_segment_vector(org, kb, segment.segment_uuid)
        is not None
    )
