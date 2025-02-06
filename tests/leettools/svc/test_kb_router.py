from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.knowledgebase import KBCreate, KBUpdate, KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.svc.api.v1.routers.kb_router import KnowledgeBaseRouter


def test_kb_router():

    context = ContextManager().get_context()

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = KnowledgeBaseRouter()
    client = TestClient(router)

    try:
        _test_router(client, context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    headers = {"username": user.username}
    org_name = org.name
    response = client.get(f"/{org_name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Add more assertions to validate the response data

    kb_name = "test"

    kb_create = KBCreate(name=kb_name, description="Sample description")
    response = client.post(f"/{org_name}", json=kb_create.model_dump(), headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    kb_new = KnowledgeBase.model_validate(response.json())
    assert kb_new.name == kb_name
    assert kb_new.description == kb_create.description

    response = client.get(f"/{org_name}/{kb_name}", headers=headers)

    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    kb_new_returned = KnowledgeBase.model_validate(response.json())
    assert kb_new_returned.name == kb_name
    assert kb_new_returned.description == kb_new.description
    assert kb_new_returned.kb_id == kb_new.kb_id

    kb_update = KBUpdate(name=kb_name, description="Updated description")
    response = client.put(
        f"/{org_name}/{kb_name}", json=kb_update.model_dump(), headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

    new_kb_name = "new_kb_name"
    kb_update = KBUpdate(
        name=kb_name, new_name=new_kb_name, description="Updated description 2"
    )
    response = client.put(
        f"/{org_name}/{kb_name}", json=kb_update.model_dump(), headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    kb_returned = KnowledgeBase.model_validate(response.json())
    assert kb_returned.name == new_kb_name
    assert kb_returned.description == "Updated description 2"
    assert kb_returned.kb_id == kb_new.kb_id

    try:
        response = client.get(f"/{org_name}/{kb_name}", headers=headers)
        assert False
    except Exception as e:
        pass

    response = client.get(f"/{org_name}/{new_kb_name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    new_kb_returned = KnowledgeBase.model_validate(response.json())
    assert new_kb_returned.name == new_kb_name
    assert new_kb_returned.description == "Updated description 2"
    assert new_kb_returned.kb_id == kb_new.kb_id

    response = client.delete(f"/{org_name}/{new_kb_name}", headers=headers)
    assert response.status_code == 200
