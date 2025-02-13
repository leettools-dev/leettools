from datetime import datetime

from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.common.utils import time_utils
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.document import DocumentCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment, SegmentCreate
from leettools.core.schemas.user import User
from leettools.svc.api.v1.routers.segment_router import SegmentRouter


def test_segment_router():

    temp_setup = TempSetup()
    context = temp_setup.context
    context.settings.DOC_STORE_TYPE = "duckdb"
    context.settings.VECTOR_STORE_TYPE = "duckdb"

    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = SegmentRouter()
    client = TestClient(router)

    try:
        _test_router(client, context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb, user)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()
    document_store = context.get_repo_manager().get_document_store()
    segment_store = context.get_repo_manager().get_segment_store()

    docsource = docsource_store.create_docsource(
        org,
        kb,
        DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.FILE,
            uri="original_docsource_uri",
            ingest_config=None,
        ),
    )

    current_docsources = docsource_store.get_docsources_for_kb(org, kb)
    assert len(current_docsources) == 1

    docsink = docsink_store.create_docsink(
        org,
        kb,
        DocSinkCreate(
            docsource=docsource,
            original_doc_uri="original_docsource_uri",
            raw_doc_uri="raw_doc_uri",
        ),
    )

    document = document_store.create_document(
        org,
        kb,
        DocumentCreate(
            docsink=docsink,
            content="content",
            doc_uri="document_uri",
        ),
    )

    headers = {"username": user.username}

    response = client.get(
        f"/{org.name}/{kb.name}/{document.document_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0

    epoch_time_ms = time_utils.cur_timestamp_in_ms()
    segment_create = SegmentCreate(
        document_uuid=document.document_uuid,
        doc_uri=document.doc_uri,
        original_uri=document.original_uri,
        docsink_uuid=document.docsink_uuid,
        kb_id=kb.kb_id,
        content="test content",
        position_in_doc="1",
        created_timestamp_in_ms=epoch_time_ms,
        label_tag=str(epoch_time_ms),
    )
    segment_store.create_segment(org=org, kb=kb, segment_create=segment_create)

    response = client.get(
        f"/{org.name}/{kb.name}/{document.document_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    segment = Segment.model_validate(response.json()[0])
    assert segment.content == "test content"
