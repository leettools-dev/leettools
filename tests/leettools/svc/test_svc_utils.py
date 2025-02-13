from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.auth.authorizer import HEADER_USERNAME_FIELD
from leettools.core.schemas.user import User
from leettools.svc.api.v1.routers.settings_router import SettingsRouter
from leettools.svc.util.svc_utils import HEADER_AUTH_UUID_FIELD


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
    headers = {"auth_provider": "google", "auth_uuid": "123456", "username": username}
    try:
        response = client.get("/", headers=headers)
    except Exception as e:
        assert e.status_code == 400
        assert e.detail == "Username should not be specified for google auth."

    headers = {
        "auth_provider": "google",
        "auth_username": "123456",
    }
    try:
        response = client.get("/", headers=headers)
    except Exception as e:
        assert e.status_code == 400
        assert (
            e.detail
            == f"{HEADER_AUTH_UUID_FIELD} not specified in the header for google."
        )

    test_username_xyz = f"{User.TEST_USERNAME_PREFIX}_xyz"
    headers = {
        "auth_provider": "google",
        "auth_uuid": "123456",
        "auth_username": test_username_xyz,
    }
    response = client.get("/", headers=headers)
    assert response.status_code == 200

    user_store = context.get_user_store()
    user = user_store.get_user_by_name(test_username_xyz)
    assert user is not None

    # since the auth_uuid is the same, the user should be the same
    wrong_name = "this_is_a_test"
    headers = {
        "auth_provider": "google",
        "auth_uuid": "123456",
        "auth_username": wrong_name,
    }
    response = client.get("/", headers=headers)
    assert response.status_code == 200

    user_store = context.get_user_store()
    user = user_store.get_user_by_name(wrong_name)
    assert user is None

    test_username_abc = f"{User.TEST_USERNAME_PREFIX}_abc"
    headers = {
        "auth_provider": "google",
        "auth_uuid": "999999999",
        "email": f"{test_username_abc}@xyz.com",
    }
    response = client.get("/", headers=headers)
    assert response.status_code == 200

    user = user_store.get_user_by_name(test_username_abc)
    assert user is not None
    assert user.username == test_username_abc
