from fastapi import HTTPException
from fastapi.testclient import TestClient

from leettools.common.exceptions import EntityNotFoundException
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy import Strategy, StrategyCreate
from leettools.core.strategy.schemas.strategy_display_settings import (
    StrategyOptionItemDisplay,
    StrategySectionDisplay,
)
from leettools.core.strategy.schemas.strategy_status import StrategyStatus
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.svc.api.v1.routers.strategy_router import StrategyRouter


def test_strategy_router():

    temp_setup = TempSetup()
    temp_setup.context.settings.DOC_STORE_TYPE = "duckdb"
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = StrategyRouter()
    client = TestClient(router)

    try:
        _test_router(client, temp_setup.context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb, user)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    strategy_store = context.get_strategy_store()

    admin_user = context.get_user_store().get_user_by_name(User.ADMIN_USERNAME)

    admin_headers = {"username": admin_user.username}

    response = client.get("/display_sections", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 7
    for x in response.json():
        assert isinstance(x, dict)
        strategy_section = StrategySectionDisplay.model_validate(x)
        assert strategy_section.section_name is not None

    response = client.get("/llm_inference_options")
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    for key in response.json().keys():
        value = response.json()[key]
        soid = StrategyOptionItemDisplay.model_validate(value)
        assert soid.name is not None

    flow_type = FlowType.DIGEST
    response = client.get(f"/flow_options/{flow_type.value}")
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, list)
    assert len(result_json) > 1
    for item in result_json:
        assert isinstance(item, dict)
        foi = FlowOptionItem.model_validate(item)
        assert foi.name is not None

    try:
        response = client.get("/strategy_types/xxxx")
    except HTTPException as e:
        assert e.status_code == 400

    response = client.get("/", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == len(
        strategy_store.list_active_strategies_for_user(user=admin_user)
    )

    default_strategy = strategy_store.get_default_strategy()
    default_strategy_id = default_strategy.strategy_id
    default_strategy_name = default_strategy.strategy_name
    assert default_strategy_id is not None
    assert default_strategy_name == "default"

    response = client.get(f"/strategy_id/{default_strategy_id}", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["strategy_name"] == default_strategy_name

    try:
        response = client.get(f"/{default_strategy_name}1", headers=admin_headers)
    except Exception as e:
        assert type(e) == EntityNotFoundException

    strategy_name = "test"
    stratey_create = StrategyCreate(strategy_name=strategy_name)
    response = client.put("/", json=stratey_create.model_dump(), headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["strategy_name"] == strategy_name
    created_strategy = Strategy.model_validate(response.json())
    strategy_id = created_strategy.strategy_id

    response = client.get("/", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == len(
        strategy_store.list_active_strategies_for_user(user=admin_user)
    )
    found = False
    for item in response.json():
        if item["strategy_id"] == strategy_id:
            found = True
            break
    assert found == True

    response = client.post(
        f"/status/{strategy_id}/{StrategyStatus.DISABLED.value}", headers=admin_headers
    )
    assert response.status_code == 200

    response = client.get(f"/strategy_id/{strategy_id}", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["strategy_status"] == StrategyStatus.DISABLED

    response = client.get("/", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == len(
        strategy_store.list_active_strategies_for_user(user=admin_user)
    )
    found = False
    for item in response.json():
        if item["strategy_id"] == strategy_id:
            found = True
            break
    assert found == False

    try:
        response = client.post(
            f"/status/{strategy_id}/{StrategyStatus.DISABLED.value}",
            headers={"username": user.username},
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 403
