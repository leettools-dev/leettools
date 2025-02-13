from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.auth.authorizer import HEADER_USERNAME_FIELD
from leettools.core.schemas.api_provider_config import (
    APIEndpointInfo,
    APIFunction,
    APIProviderConfig,
)
from leettools.core.schemas.user import User
from leettools.core.schemas.user_settings import UserSettings, UserSettingsUpdate
from leettools.settings import HTML_EXT, MD_EXT, PDF_EXT, TXT_EXT
from leettools.svc.api.v1.routers.settings_router import SettingsRouter


def test_settings_router():

    temp_setup = TempSetup()
    context = ContextManager().get_context()  # type: Context
    user = temp_setup.create_tmp_user()
    user_store = context.get_user_store()
    admin_user = user_store.get_user_by_name(User.ADMIN_USERNAME)

    router = SettingsRouter()
    client = TestClient(router)

    try:
        _test_router(client, context, user)
    finally:
        temp_setup.delete_tmp_user(user)
        assert user_store._get_dbname_for_test().endswith("_test")
        user_store.delete_user_by_id(admin_user.user_uuid)


def _test_router(client: TestClient, context: Context, user: User):

    try:
        response = client.get("/")
    except Exception as e:
        assert e.status_code == 400
        assert e.detail == f"{HEADER_USERNAME_FIELD} not specified in the header"

    response = client.get("/supported_api_functions")
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, list)
    assert len(result_json) == 3

    # add username to the request header
    headers = {"username": "test_user_xyzabc"}
    try:
        response = client.get("/", headers=headers)
    except Exception as e:
        assert e.status_code == 404
        assert e.detail == "User test_user_xyzabc not found"

    username = user.username
    headers = {"username": username}

    response = client.get("/supported_file_extensions", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, list)
    assert len(result_json) == 9
    assert HTML_EXT in result_json
    assert MD_EXT in result_json
    assert PDF_EXT in result_json
    assert TXT_EXT in result_json

    response = client.get("/", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    result_settings = UserSettings.model_validate(result_json)

    assert result_settings.username == username
    assert result_settings.user_uuid == user.user_uuid
    assert result_settings.created_at == result_settings.updated_at

    default_settings = context.settings.get_user_configurable_settings()
    assert result_settings.settings == default_settings

    # update settings
    assert "LLM_API_KEY" in default_settings
    old_item = default_settings["LLM_API_KEY"]
    new_item = old_item.model_copy()
    new_item.value = "new_key"
    settings_update = UserSettingsUpdate(
        username=user.username,
        user_uuid=user.user_uuid,
        settings={"LLM_API_KEY": new_item},
    )

    response = client.put("/", headers=headers, json=settings_update.model_dump())
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    result_settings = UserSettings.model_validate(result_json)
    assert result_settings.created_at < result_settings.updated_at
    assert len(result_settings.settings) == len(default_settings)
    assert result_settings.settings["LLM_API_KEY"].value == "new_key"

    response = client.get("/api_providers", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    assert len(result_json) == 2

    api_provider_config = APIProviderConfig(
        api_provider="test",
        api_key="xyz",
        base_url="123",
        endpoints={APIFunction.EMBED: APIEndpointInfo()},
    )
    response = client.put(
        "/api_provider", headers=headers, json=api_provider_config.model_dump()
    )
    assert response.status_code == 200
    result_json = response.json()
    result_api_provider = APIProviderConfig.model_validate(result_json)
    assert result_api_provider.api_provider == "test"
    assert result_api_provider.api_key == "xyz"
    assert result_api_provider.base_url == "123"
    assert len(result_api_provider.endpoints) == 1

    api_provider_config = APIProviderConfig(
        api_provider="test",
        api_key="abc",
        base_url="123",
        endpoints={
            APIFunction.INFERENCE: APIEndpointInfo(),
            APIFunction.EMBED: APIEndpointInfo(),
            APIFunction.RERANK: APIEndpointInfo(),
        },
    )
    response = client.put(
        "/api_provider", headers=headers, json=api_provider_config.model_dump()
    )
    assert response.status_code == 200
    result_json = response.json()
    result_api_provider = APIProviderConfig.model_validate(result_json)
    assert result_api_provider.api_provider == "test"
    assert result_api_provider.api_key == "abc"
    assert result_api_provider.base_url == "123"
    assert len(result_api_provider.endpoints) == 3

    response = client.get("/api_providers", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    assert len(result_json[username]) == 1

    response = client.get(f"/api_provider/{username}/test", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    result_api_provider = APIProviderConfig.model_validate(result_json)
    assert result_api_provider.api_provider == "test"
    assert result_api_provider.api_key == "abc"
    assert result_api_provider.base_url == "123"
    assert len(result_api_provider.endpoints) == 3

    api_provider_config = APIProviderConfig(
        api_provider="admin_test",
        api_key="abc",
        base_url="123",
        endpoints={
            APIFunction.INFERENCE: APIEndpointInfo(),
            APIFunction.EMBED: APIEndpointInfo(),
            APIFunction.RERANK: APIEndpointInfo(),
        },
    )
    response = client.put(
        "/api_provider",
        headers={"username": User.ADMIN_USERNAME},
        json=api_provider_config.model_dump(),
    )
    assert response.status_code == 200
    result_json = response.json()
    result_api_provider = APIProviderConfig.model_validate(result_json)
    assert result_api_provider.api_provider == "admin_test"
    assert result_api_provider.api_key == "abc"
    assert result_api_provider.base_url == "123"
    assert len(result_api_provider.endpoints) == 3

    response = client.get("/api_providers", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    assert len(result_json) == 2
    assert len(result_json[username]) == 1
    assert len(result_json[User.ADMIN_USERNAME]) == 1

    api_provider_config_user = APIProviderConfig.model_validate(
        result_json[username][0]
    )
    assert api_provider_config_user.api_provider == "test"

    api_provider_config_admin = APIProviderConfig.model_validate(
        result_json[User.ADMIN_USERNAME][0]
    )
    assert api_provider_config_admin.api_provider == "admin_test"
