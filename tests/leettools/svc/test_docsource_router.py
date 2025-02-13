from typing import Dict, List

from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSource, DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.svc.api.v1.routers.docsource_router import DocSourceRouter


def test_docsource_router():

    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = DocSourceRouter()
    client = TestClient(router)

    try:
        _test_router(client, context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    docsource_store = context.get_repo_manager().get_docsource_store()

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

    headers = {"username": user.username}

    response = client.get("/types", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # right now we have 9 types
    assert len(response.json()) == 9

    response = client.get(f"/{org.name}/{kb.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == len(current_docsources)

    docsource = current_docsources[0]

    response = client.get(
        f"/{org.name}/{kb.name}/{docsource.docsource_uuid}", headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["docsource_uuid"] == docsource.docsource_uuid

    # TODO: right now we are not testing the post, put and delete methods
    # should add when we have a good way to set up the tests

    response = client.get(f"/{org.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

    docsources_for_org: Dict[str, List[DocSource]] = {}
    for kb_name, docsources in response.json().items():
        assert isinstance(kb_name, str)
        assert isinstance(docsources, list)
        docsources_for_kb: List[DocSource] = []
        for docsource in docsources:
            docsources_for_kb.append(DocSource.model_validate(docsource))
        docsources_for_org[kb_name] = docsources_for_kb
    assert len(docsources_for_org) == 1
