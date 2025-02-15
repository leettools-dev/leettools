from fastapi import HTTPException
from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.knowledgebase import KBCreate, KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.svc.api.v1.routers.kb_router import KnowledgeBaseRouter


def test_kb_router():

    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user_01 = temp_setup.create_tmp_org_kb_user()

    user_02 = temp_setup.create_tmp_user("test_user_002")

    router = KnowledgeBaseRouter()
    client = TestClient(router)

    try:
        _test_router_share(client, context, org, kb, user_01, user_02)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb, user_01)
        temp_setup.delete_tmp_user(user_02)


def _test_router_share(
    client: TestClient,
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    user_01: User,
    user_02: User,
) -> None:

    headers_01 = {"username": user_01.username}
    headers_02 = {"username": user_02.username}
    org_name = org.name
    response = client.get(f"/{org_name}", headers=headers_01)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Add more assertions to validate the response data

    kb_name_01 = "test_01"
    kb_create = KBCreate(name=kb_name_01, description="Sample description 01")
    response = client.post(
        f"/{org_name}", json=kb_create.model_dump(), headers=headers_01
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    kb_new = KnowledgeBase.model_validate(response.json())
    assert kb_new.name == kb_name_01
    assert kb_new.description == kb_create.description

    response = client.get(f"/{org_name}/{kb_name_01}", headers=headers_01)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    kb_new_returned = KnowledgeBase.model_validate(response.json())
    assert kb_new_returned.name == kb_name_01
    assert kb_new_returned.description == kb_new.description
    assert kb_new_returned.kb_id == kb_new.kb_id
    assert kb_new_returned.share_to_public == False

    response = client.get(f"/{org_name}", headers=headers_02)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0

    try:
        response = client.get(f"/{org_name}/{kb_name_01}", headers=headers_02)
    except HTTPException as e:
        assert e.status_code == 403

    kb_name_02 = "test_02"
    kb_create = KBCreate(name=kb_name_02, description="Sample description 02")
    response = client.post(
        f"/{org_name}", json=kb_create.model_dump(), headers=headers_01
    )
    assert response.status_code == 200

    response = client.get(f"/{org_name}", headers=headers_01)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 3

    response = client.get(f"/{org_name}", headers=headers_02)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0

    # now share the first kb to public
    response = client.post(f"/share/{org_name}/{kb_name_01}", headers=headers_01)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    kb_udpated_returned = KnowledgeBase.model_validate(response.json())
    assert kb_udpated_returned.name == kb_name_01
    assert kb_udpated_returned.description == kb_new.description
    assert kb_udpated_returned.kb_id == kb_new.kb_id
    assert kb_udpated_returned.share_to_public == True

    # user 02 can get the kb_01

    response = client.get(f"/{org_name}", headers=headers_02)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1

    response = client.get(f"/{org_name}/{kb_name_01}", headers=headers_02)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    kb_new_returned = KnowledgeBase.model_validate(response.json())
    assert kb_new_returned.name == kb_name_01
    assert kb_new_returned.description == kb_new.description
    assert kb_new_returned.kb_id == kb_new.kb_id

    # still can't get the kb_02
    try:
        response = client.get(f"/{org_name}/{kb_name_02}", headers=headers_02)
    except HTTPException as e:
        assert e.status_code == 403

    # user 02 can't share / unshare the kb_01
    try:
        response = client.post(f"/share/{org_name}/{kb_name_01}", headers=headers_02)
    except HTTPException as e:
        assert e.status_code == 403

    try:
        response = client.post(f"/unshare/{org_name}/{kb_name_01}", headers=headers_02)
    except HTTPException as e:
        assert e.status_code == 403

    # admin user can't share kb_02
    headers_admin = {"username": "admin"}
    try:
        response = client.post(f"/share/{org_name}/{kb_name_02}", headers=headers_admin)
    except HTTPException as e:
        assert e.status_code == 403

    # admin user can unshare kb_01
    response = client.post(f"/unshare/{org_name}/{kb_name_01}", headers=headers_admin)
    assert response.status_code == 200

    # now user 02 can't get the kb_01
    try:
        response = client.get(f"/{org_name}/{kb_name_01}", headers=headers_02)
    except HTTPException as e:
        assert e.status_code == 403
