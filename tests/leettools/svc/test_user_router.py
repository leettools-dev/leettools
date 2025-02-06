import random

from fastapi.testclient import TestClient

from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.user import User, UserCreate
from leettools.svc.api.v1.routers.user_router import UserRouter


def test_user_router():

    context = ContextManager().get_context()  # type: Context
    context.reset(is_test=True)

    router = UserRouter()
    client = TestClient(router)

    user_store = context.get_user_store()
    user_settings_store = context.get_user_settings_store()
    assert user_settings_store is not None

    try:
        response = client.get("/")
    except Exception as e:
        assert e.status_code == 400
        assert (
            e.detail == "User name must be provided in the username field in the header"
        )

    # add username to the request header and the check shoudl fail
    headers = {"username": "test_user_xyzabc"}
    try:
        response = client.get("/", headers=headers)
    except Exception as e:
        assert e.status_code == 404
        assert e.detail == "User test_user_xyzabc not found"

    # the User.ADMIN_USERNAME should exist automatically
    headers = {"username": User.ADMIN_USERNAME}
    response = client.get(f"/{User.ADMIN_USERNAME}", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    result_user = User.model_validate(result_json)
    assert result_user.username == User.ADMIN_USERNAME

    # create a user using the admin user
    username = f"test_user_{random.randint(1000, 9999)}"
    user_create = UserCreate(username=username)
    response = client.put("/", headers=headers, json=user_create.model_dump())

    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    result_new_user = User.model_validate(result_json)
    assert result_new_user.username == username

    # but creating anothe user with the new user won't work
    username2 = f"test_user_{random.randint(1000, 9999)}"
    headers = {"username": username}
    user_create = UserCreate(username=username2)
    try:
        response = client.put("/", headers=headers, json=user_create.model_dump())
    except Exception as e:
        assert e.status_code == 403
        assert e.detail == f"Only {User.ADMIN_USERNAME} is allowed to access this API"

    # the user should be able to get their own user
    headers = {"username": username}
    response = client.get(f"/{username}", headers=headers)
    assert response.status_code == 200
    result_json = response.json()
    assert isinstance(result_json, dict)
    result_user = User.model_validate(result_json)
    assert result_user.username == username

    user_store.delete_user_by_id(result_new_user.user_uuid)
