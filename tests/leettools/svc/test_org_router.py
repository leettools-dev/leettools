import pytest
from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.svc.api.v1.routers.org_router import OrgRouter


def test_org_router():

    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = OrgRouter()
    client = TestClient(router)

    try:
        _test_router(client, context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase
) -> None:

    response1 = client.get(f"/default")
    assert response1.status_code == 200
    assert isinstance(response1.json(), dict)
    assert context.settings.DEFAULT_ORG_NAME == response1.json()["name"]

    response2 = client.get(f"/{context.settings.DEFAULT_ORG_NAME}")
    assert response2.status_code == 200
    assert isinstance(response2.json(), dict)

    assert response1.json() == response2.json()

    response3 = client.get(f"/")
    assert response3.status_code == 200
    assert isinstance(response3.json(), list)
