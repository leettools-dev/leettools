from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.document import Document, DocumentCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.svc.api.v1.routers.document_router import DocumentRouter


def test_document_router():
    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "duckdb"
    temp_setup.context.settings.VECTOR_STORE_TYPE = "duckdb"
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = DocumentRouter()
    client = TestClient(router)

    try:
        _test_router(client, temp_setup.context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()
    document_store = context.get_repo_manager().get_document_store()

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

    response = client.get(f"/{org.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert len(response.json()) == 1
    for kb_name in response.json():
        assert kb_name == kb.name
        assert isinstance(response.json()[kb_name], list)
        assert len(response.json()[kb_name]) == 1
        doc_json = response.json()[kb_name][0]
        returned_document = Document.model_validate(doc_json)
        assert returned_document.content == ""
        assert returned_document.doc_uri == document.doc_uri
        assert returned_document.docsink_uuid == document.docsink_uuid
        assert returned_document.docsource_uuids == document.docsource_uuids
        assert returned_document.kb_id == document.kb_id
        assert returned_document.document_uuid == document.document_uuid

    response = client.get(f"/{org.name}/{kb.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    doc_json = response.json()[0]
    returned_document = Document.model_validate(doc_json)
    assert returned_document.content == ""
    assert returned_document.doc_uri == document.doc_uri
    assert returned_document.docsink_uuid == document.docsink_uuid
    assert returned_document.docsource_uuids == document.docsource_uuids
    assert returned_document.kb_id == document.kb_id
    assert returned_document.document_uuid == document.document_uuid

    response = client.get(
        f"/{org.name}/{kb.name}/docsource/{docsource.docsource_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    doc_json = response.json()[0]
    returned_document = Document.model_validate(doc_json)
    assert returned_document.content == ""

    try:
        response = client.get(
            f"/{org.name}/{kb.name}/docsource/non_existing_uuid", headers=headers
        )
        raise AssertionError("Expected 404")
    except Exception as e:
        pass

    response = client.get(
        f"/{org.name}/{kb.name}/docsink/{docsink.docsink_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    doc_json = response.json()[0]
    returned_document = Document.model_validate(doc_json)
    assert returned_document.content == "content"

    response = client.get(f"/{org.name}/{kb.name}/docsource_type", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert len(response.json()) == 1
    ds_type = list(response.json().keys())[0]
    assert ds_type == DocSourceType.FILE.value

    doc_list = response.json()[ds_type]
    assert isinstance(doc_list, list)
    assert len(doc_list) == 1
    doc = doc_list[0]
    returned_document = Document.model_validate(doc)
    assert returned_document.document_uuid == document.document_uuid
    assert returned_document.docsource_type == DocSourceType.FILE

    response = client.get(
        f"/{org.name}/{kb.name}/docsource_type?docsource_type={DocSourceType.FILE.value}",
        headers=headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert len(response.json()) == 1
    ds_type = list(response.json().keys())[0]
    assert ds_type == DocSourceType.FILE.value

    doc_list = response.json()[ds_type]
    assert isinstance(doc_list, list)
    assert len(doc_list) == 1
    doc = doc_list[0]
    returned_document = Document.model_validate(doc)
    assert returned_document.document_uuid == document.document_uuid
    assert returned_document.docsource_type == DocSourceType.FILE

    response = client.delete(
        f"/{org.name}/{kb.name}/{document.document_uuid}", headers=headers
    )
    assert response.status_code == 200

    response = client.get(
        f"/{org.name}/{kb.name}/docsink/{docsink.docsink_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0
