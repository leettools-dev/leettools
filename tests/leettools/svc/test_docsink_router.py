import random
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.svc.api.v1.routers.docsink_router import DocSinkRouter


def test_permission_docsink_router():
    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "mongo"
    temp_setup.context.settings.VECTOR_STORE_TYPE = "milvus"

    context = temp_setup.context
    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)
    org, kb, admin_user = temp_setup.create_tmp_org_kb_user(admin_user)

    router = DocSinkRouter()
    client = TestClient(router)

    user = temp_setup.create_tmp_user()
    try:
        _test_user_access_admin(client, context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb, user)


def test_multiuser_permission_docsink_router():
    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "mongo"
    temp_setup.context.settings.VECTOR_STORE_TYPE = "milvus"

    user1 = temp_setup.create_tmp_user()
    org, kb, user1 = temp_setup.create_tmp_org_kb_user(user1)

    router = DocSinkRouter()
    client = TestClient(router)

    user2 = temp_setup.create_tmp_user()
    try:
        _test_user_access_user(client, temp_setup.context, org, kb, user2)
    finally:
        temp_setup.delete_tmp_user(user2)
        temp_setup.delete_tmp_user(user1)
        temp_setup.clear_tmp_org_kb_user(org, kb)


def test_regular_docsink_router():
    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "mongo"
    temp_setup.context.settings.VECTOR_STORE_TYPE = "milvus"
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    context = temp_setup.context
    router = DocSinkRouter()
    client = TestClient(router)

    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)
    try:
        _test_regular_router(client, context, org, kb, user)
        _test_regular_router(client, context, org, kb, admin_user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb, user)


def _create_docsource_docsink(context: Context, org: Org, kb: KnowledgeBase):
    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()

    docsource = docsource_store.create_docsource(
        org,
        kb,
        DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.FILE,
            uri=f"original_docsource_uri_{random.randint(0, 1000)}",
            ingest_config=None,
        ),
    )

    current_docsources = docsource_store.get_docsources_for_kb(org, kb)
    assert len(current_docsources) >= 1

    docsink = docsink_store.create_docsink(
        org,
        kb,
        DocSinkCreate(
            docsource=docsource,
            original_doc_uri=docsource.uri,
            raw_doc_uri=f"raw_doc_uri_{random.randint(0, 1000)}",
        ),
    )
    assert docsink is not None
    assert docsink.docsink_uuid is not None
    current_docsink = docsink_store.get_docsink_by_id(org, kb, docsink.docsink_uuid)
    assert current_docsink is not None
    assert current_docsink.docsource_uuids[0] == docsource.docsource_uuid
    return docsource, docsink


def _test_user_access_user(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
):
    docsource, docsink = _create_docsource_docsink(context, org, kb)
    headers = {"username": user.username}
    response = client.get(f"/{org.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert len(response.json()) == 0

    try:
        response = client.get(f"/{org.name}/{kb.name}", headers=headers)
    except HTTPException as e:
        assert e.status_code == 403

    try:
        response = client.get(
            f"/{org.name}/{kb.name}/{docsource.docsource_uuid}", headers=headers
        )
    except HTTPException as e:
        assert e.status_code == 403

    try:
        response = client.delete(
            f"/{org.name}/{kb.name}/{docsource.docsource_uuid}/{docsink.docsink_uuid}",
            headers=headers,
        )
    except HTTPException as e:
        assert e.status_code == 403


def _test_user_access_admin(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
):
    docsource, docsink = _create_docsource_docsink(context, org, kb)
    headers = {"username": user.username}
    response = client.get(f"/{org.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert len(response.json()[kb.name]) == 1
    for sink in response.json()[kb.name]:
        assert sink["docsource_uuids"] == [docsource.docsource_uuid]
        assert sink["kb_id"] == kb.kb_id
        assert str(sink["original_doc_uri"]).startswith("original_docsource_uri")
        assert str(sink["raw_doc_uri"]).startswith("raw_doc_uri")
        assert sink["docsink_uuid"] == docsink.docsink_uuid

    response = client.get(f"/{org.name}/{kb.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    sink = response.json()[0]
    assert sink["docsource_uuids"] == [docsource.docsource_uuid]
    assert sink["kb_id"] == kb.kb_id
    assert str(sink["original_doc_uri"]).startswith("original_docsource_uri")
    assert str(sink["raw_doc_uri"]).startswith("raw_doc_uri")
    assert sink["docsink_uuid"] == docsink.docsink_uuid

    response = client.get(
        f"/{org.name}/{kb.name}/{docsource.docsource_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for sink in response.json():
        assert sink["docsource_uuids"] == [docsource.docsource_uuid]
        assert sink["kb_id"] == kb.kb_id
        assert str(sink["original_doc_uri"]).startswith("original_docsource_uri")
        assert str(sink["raw_doc_uri"]).startswith("raw_doc_uri")
        assert sink["docsink_uuid"] == docsink.docsink_uuid

    try:
        response = client.delete(
            f"/{org.name}/{kb.name}/{docsource.docsource_uuid}/{docsink.docsink_uuid}",
            headers=headers,
        )
    except HTTPException as e:
        assert e.status_code == 403

    response = client.get(
        f"/{org.name}/{kb.name}/{docsource.docsource_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for sink in response.json():
        assert sink["docsource_uuids"] == [docsource.docsource_uuid]
        assert sink["kb_id"] == kb.kb_id
        assert str(sink["original_doc_uri"]).startswith("original_docsource_uri")
        assert str(sink["raw_doc_uri"]).startswith("raw_doc_uri")
        assert sink["docsink_uuid"] == docsink.docsink_uuid


def _test_regular_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
):
    docsource, docsink = _create_docsource_docsink(context, org, kb)

    headers = {"username": user.username}
    response = client.get(f"/{org.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    results: Dict[str, Any] = response.json()
    assert len(results[kb.name]) == 1
    for sink in response.json()[kb.name]:
        assert sink["docsource_uuids"] == [docsource.docsource_uuid]
        assert sink["kb_id"] == kb.kb_id
        assert str(sink["original_doc_uri"]).startswith("original_docsource_uri")
        assert str(sink["raw_doc_uri"]).startswith("raw_doc_uri")
        assert sink["docsink_uuid"] == docsink.docsink_uuid

    response = client.get(f"/{org.name}/{kb.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    sink = response.json()[0]
    assert sink["docsource_uuids"] == [docsource.docsource_uuid]
    assert sink["kb_id"] == kb.kb_id
    assert str(sink["original_doc_uri"]).startswith("original_docsource_uri")
    assert str(sink["raw_doc_uri"]).startswith("raw_doc_uri")
    assert sink["docsink_uuid"] == docsink.docsink_uuid

    response = client.get(
        f"/{org.name}/{kb.name}/{docsource.docsource_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for sink in response.json():
        assert sink["docsource_uuids"] == [docsource.docsource_uuid]
        assert sink["kb_id"] == kb.kb_id
        assert str(sink["original_doc_uri"]).startswith("original_docsource_uri")
        assert str(sink["raw_doc_uri"]).startswith("raw_doc_uri")
        assert sink["docsink_uuid"] == docsink.docsink_uuid

    response = client.delete(
        f"/{org.name}/{kb.name}/{docsource.docsource_uuid}/{docsink.docsink_uuid}",
        headers=headers,
    )
    assert response.status_code == 200

    try:
        response = client.get(
            f"/{org.name}/{kb.name}/{docsource.docsource_uuid}", headers=headers
        )
    except HTTPException as e:
        assert e.status_code == 404
