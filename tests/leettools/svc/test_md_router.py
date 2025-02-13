import httpx
from fastapi.testclient import TestClient

from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.document import DocumentCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.svc.api.v1.routers.md_router import MDRouter


def test_md_router():
    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "duckdb"
    temp_setup.context.settings.VECTOR_STORE_TYPE = "duckdb"

    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = MDRouter()
    client = TestClient(router)

    try:
        _test_router(client, temp_setup.context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase
) -> None:

    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()
    doc_store = context.get_repo_manager().get_document_store()

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

    docsink = docsink_store.create_docsink(
        org,
        kb,
        DocSinkCreate(
            docsource=docsource,
            original_doc_uri="original_docsource_uri",
            raw_doc_uri="raw_doc_uri",
        ),
    )

    doc_create = DocumentCreate(
        docsink=docsink,
        content="test content",
        doc_uri="converted_document_uri",
    )

    doc = doc_store.create_document(org, kb, doc_create)
    assert doc is not None
    assert doc.document_uuid is not None

    logger().info(f"Created document with UUID: {doc.document_uuid}")

    """
            kb_id: str,
            doc_uuid: str,
            start_offset: Optional[int] = None,
            end_offset: Optional[int] = None,
            format: str = Query("json", enum=["json", "html"]),
    """

    result = client.get(
        f"/?org_name={org.name}&kb_name={kb.name}&doc_uuid={doc.document_uuid}"
    )
    assert result.status_code == 200
    # print(result.json())
    assert isinstance(result.json(), dict)
    assert "html_content" in result.json()

    result: httpx.Response = client.get(
        f"/?org_name={org.name}&kb_name={kb.name}&doc_uuid={doc.document_uuid}&format=html"
    )
    print(result.text)
    assert result.status_code == 200
    assert "test content" in result.text

    result: httpx.Response = client.get(
        f"/?org_name={org.name}&kb_name={kb.name}&doc_uuid={doc.document_uuid}"
        "&format=html&start_offset=0&end_offset=4"
    )
    print(result.text)
    assert result.status_code == 200
    assert "test content" not in result.text
