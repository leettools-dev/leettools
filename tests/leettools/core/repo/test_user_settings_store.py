from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.api_provider_config import APIFunction, APIProviderConfig
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.schemas.user_settings import (
    UserSettings,
    UserSettingsItem,
    UserSettingsUpdate,
)
from leettools.eds.api_caller.api_utils import get_api_function_list


def test_user_settings_store():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        logger().info(f"Testing with store_types: {store_types}")

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_settings_store(context, org, kb, user)
            _test_api_config_provider(context, org, kb, user)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb, user)
            logger().info(f"Cleared temp org, kb, user for store_types: {store_types}")


def _test_settings_store(context: Context, org: Org, kb: KnowledgeBase, user: User):

    user_settings_store = context.get_user_settings_store()

    user_settings: UserSettings = user_settings_store.get_settings_for_user(user)
    assert user_settings is not None
    assert user_settings.user_uuid == user.user_uuid
    assert user_settings.username == user.username
    assert user_settings.user_settings_id is not None
    assert user_settings.settings is not None

    default_settings = context.settings.get_user_configurable_settings()
    assert len(user_settings.settings) == len(default_settings)
    assert user_settings.settings["LLM_API_KEY"].value == None

    for key in user_settings.settings:
        assert user_settings.settings[key] == default_settings[key]

    # Update the settings
    old_item = user_settings.settings["LLM_API_KEY"]
    new_item = old_item.model_copy()
    new_item.value = "new_key"
    settings_update = UserSettingsUpdate(
        username=user.username,
        user_uuid=user.user_uuid,
        settings={"LLM_API_KEY": new_item},
    )

    new_user_settings = user_settings_store.update_settings_for_user(
        user, settings_update
    )
    assert new_user_settings is not None
    assert new_user_settings.user_uuid == user.user_uuid
    assert new_user_settings.settings["LLM_API_KEY"].value == "new_key"
    # when storing to DB, the time_utils.current_datetime() may lose the microsecond
    # 2024-04-20 23:44:18.609678 -> 2024-04-20 23:44:18.609000
    # so need to be careful when comparing the datetime
    assert new_user_settings.updated_at > user_settings.updated_at

    # Get the settings again
    user_settings = user_settings_store.get_settings_for_user(user)

    assert user_settings is not None
    assert user_settings.user_settings_id == new_user_settings.user_settings_id
    assert user_settings.user_uuid == user.user_uuid
    assert user_settings.settings["LLM_API_KEY"].value == "new_key"
    assert user_settings.updated_at == new_user_settings.updated_at

    # Add a new item to the settings
    settings_update.settings["NEW_SETTING"] = UserSettingsItem(
        section="section",
        name="NEW_SETTING",
        value="new_value",
        description="new setting",
        value_type="str",
        default_value="new_default_value",
    )
    new_user_settings = user_settings_store.update_settings_for_user(
        user, settings_update
    )
    user_settings = user_settings_store.get_settings_for_user(user)
    assert user_settings is not None
    assert user_settings.user_uuid == user.user_uuid
    assert user_settings.settings["LLM_API_KEY"].value == "new_key"
    assert user_settings.settings["NEW_SETTING"].value == "new_value"


def _test_api_config_provider(
    context: Context, org: Org, kb: KnowledgeBase, user: User
):

    api_function_list = get_api_function_list()
    assert len(api_function_list) == 3
    assert APIFunction.EMBED in api_function_list
    assert APIFunction.INFERENCE in api_function_list
    assert APIFunction.RERANK in api_function_list

    user_store = context.get_user_store()
    user_settings_store = context.get_user_settings_store()

    api_providers = user_settings_store.get_all_api_provider_configs_for_user(user)
    assert len(api_providers) == 0

    api_provider_config = APIProviderConfig(
        api_provider="test1", api_key="xyz", base_url="123", endpoints={}
    )
    user_settings_store.add_api_provider_config(user, api_provider_config)

    api_providers = user_settings_store.get_all_api_provider_configs_for_user(user)
    assert len(api_providers) == 1
    assert api_providers[0].api_provider == "test1"
    assert api_providers[0].api_key == "xyz"
    assert api_providers[0].base_url == "123"

    api_provider_config = APIProviderConfig(
        api_provider="test1", api_key="abc", base_url="123", endpoints={}
    )
    user_settings_store.add_api_provider_config(user, api_provider_config)
    api_providers = user_settings_store.get_all_api_provider_configs_for_user(user)
    assert len(api_providers) == 1
    assert api_providers[0].api_provider == "test1"
    assert api_providers[0].api_key == "abc"
    assert api_providers[0].base_url == "123"

    api_provider_config = APIProviderConfig(
        api_provider="test2", api_key="abc", base_url="123", endpoints={}
    )
    user_settings_store.add_api_provider_config(user, api_provider_config)
    api_providers = user_settings_store.get_all_api_provider_configs_for_user(user)
    assert len(api_providers) == 2

    api_provider_config = user_settings_store.get_api_provider_config_by_name(
        user, "test2"
    )
    assert api_provider_config.api_provider == "test2"
    assert api_provider_config.api_key == "abc"
    assert api_provider_config.base_url == "123"
