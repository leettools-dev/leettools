from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.accouting import INIT_BALANCE
from leettools.core.schemas.api_provider_config import (
    APIEndpointInfo,
    APIFunction,
    APIProviderConfig,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User, UserCreate, UserUpdate


def test_userstore():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]
        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):
    userstore = context.get_user_store()
    userstore._reset_for_test()

    # Test create_user
    user_create = UserCreate(
        username=f"{User.TEST_USERNAME_PREFIX}_user1",
        full_name="User One",
    )
    user1 = userstore.create_user(user_create)
    assert user1.user_uuid is not None
    assert user1.balance == INIT_BALANCE
    logger().info(f"Created user with UUID: {user1.user_uuid}")

    user1 = userstore.change_user_balance(user1.user_uuid, 100)
    assert user1.balance == INIT_BALANCE + 100

    user1 = userstore.change_user_balance(user1.user_uuid, -25)
    assert user1.balance == INIT_BALANCE + 75

    user_create = UserCreate(
        username=f"{User.TEST_USERNAME_PREFIX}_user2",
        full_name="User Two",
    )
    user2 = userstore.create_user(user_create)
    assert user2.user_uuid is not None
    logger().info(f"Created user with UUID: {user2.user_uuid}")

    # Test update_user
    user_update = UserUpdate(
        user_uuid=user1.user_uuid,
        username=user1.username,
        email="test@example.com",
        full_name="User One Updated",
    )

    user3 = userstore.update_user(user_update)
    assert user3 is not None
    assert user3.full_name == "User One Updated"
    logger().info(f"Updated user with UUID: {user3.user_uuid}")

    # Test get_user
    user4 = userstore.get_user_by_uuid(user1.user_uuid)
    assert user4 is not None
    assert user4.full_name == "User One Updated"

    # Test get_user_by_email
    user5 = userstore.get_user_by_email("test@example.com")
    assert user5 is not None
    assert user5.full_name == "User One Updated"

    # Test get_users
    users = userstore.get_users()
    assert len(users) == 3  # 3 because the admin user is created automatically
    logger().info(f"Retrieved {len(users)} users")

    # Test delete_user
    user_uuid = user1.user_uuid
    deleted = userstore.delete_user_by_id(user_uuid)
    assert deleted
    logger().info(f"Deleted user with UUID: {user_uuid}")

    # Test get_user
    user6 = userstore.get_user_by_uuid(user1.user_uuid)
    assert user6 is None
    logger().info(f"Retrieved user with UUID: {user1.user_uuid} after delete")

    # Test get_users
    users = userstore.get_users()
    assert len(users) == 2

    user_settings_store = context.get_user_settings_store()
    user_settings_store._reset_for_test(users[0].user_uuid)

    # test get_settings_for_user
    user_settings = user_settings_store.get_settings_for_user(users[0])
    assert user_settings is not None

    # test update_settings_for_user
    user_settings_update = user_settings.model_copy()
    logger().info(f"User settings: {user_settings_update}")
    user_settings_update.settings["OPENAI_API_KEY"].value = "test"

    user_settings = user_settings_store.update_settings_for_user(
        users[0], user_settings_update
    )
    user_settings_1 = user_settings_store.get_settings_for_user(users[0])
    assert user_settings_1 is not None
    assert user_settings_1.settings["OPENAI_API_KEY"].value == "test"

    # test add_api_provider_config
    api_provider_config = APIProviderConfig(
        api_provider="test",
        api_key="test",
        base_url="https://test.com",
        endpoints={
            APIFunction.EMBED: APIEndpointInfo(path="/embed", default_model="test"),
        },
    )
    user_settings_store.add_api_provider_config(users[0], api_provider_config)

    # test get_api_provider_config_by_name
    api_provider_config = user_settings_store.get_api_provider_config_by_name(
        users[0], "test"
    )
    assert api_provider_config is not None

    # test get_all_api_provider_configs_for_user
    api_provider_configs = user_settings_store.get_all_api_provider_configs_for_user(
        users[0]
    )
    assert len(api_provider_configs) == 1
