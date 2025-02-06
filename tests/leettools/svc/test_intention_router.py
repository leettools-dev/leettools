from fastapi import HTTPException
from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.intention import (
    Intention,
    IntentionCreate,
    IntentionUpdate,
)
from leettools.svc.api.v1.routers.intention_router import IntentionRouter


def test_intention_router():
    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "mongo"
    org, kb, user = temp_setup.create_tmp_org_kb_user()
    intention_store = temp_setup.context.get_intention_store()

    router = IntentionRouter()
    client = TestClient(router)

    try:
        _test_router(client, temp_setup.context, org, kb, user)
    finally:
        intention_store._reset_for_test()
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    intention_store = context.get_intention_store()
    assert intention_store is not None

    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)
    headers = {"username": admin_user.username}

    response = client.get("/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == len(intention_store.get_all_intentions())

    intention_name = "test_intention"
    try:
        response = client.get(f"/{intention_name}", headers=headers)
    except HTTPException as e:
        assert e.status_code == 404

    intention_create = IntentionCreate(intention=intention_name)
    response = client.put("/", json=intention_create.model_dump(), headers=headers)
    assert response.status_code == 200
    intention = Intention.model_validate(response.json())
    assert intention.intention == intention_name
    assert intention.display_name == intention_name
    assert intention.description is None
    assert intention.examples == []
    assert intention.is_active == True

    response = client.get(f"/{intention_name}", headers=headers)
    assert response.status_code == 200
    intention = Intention.model_validate(response.json())
    assert intention.intention == intention_name

    intention_update = IntentionUpdate(
        intention=intention_name,
        description=intention.description,
        display_name=intention.display_name,
        examples=["example1", "example2"],
        is_active=False,
    )
    response = client.post("/", json=intention_update.model_dump(), headers=headers)
    assert response.status_code == 200
    intention = Intention.model_validate(response.json())
    assert intention.intention == intention_name
    assert intention.display_name == intention_name
    assert intention.description is None
    assert intention.examples == ["example1", "example2"]
    assert intention.is_active == False
