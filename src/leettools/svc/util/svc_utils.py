import random
from typing import Optional

from fastapi import HTTPException

from leettools.core.auth.authorizer import HEADER_AUTH_UUID_FIELD
from leettools.core.schemas.user import User, UserCreate


def get_user_with_auth(
    auth_provider: str,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    auth_uuid: Optional[str] = None,
    auth_username: Optional[str] = None,
) -> User:
    if auth_uuid is None:
        raise HTTPException(
            status_code=400,
            detail=f"{HEADER_AUTH_UUID_FIELD} not specified in the header for {auth_provider}.",
        )

    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    user_store = context.get_user_store()

    # potential race condition here
    user = user_store.get_user_by_auth_uuid(auth_provider, auth_uuid)

    if user is not None:
        return user

    if auth_username is None or auth_username == "":
        if email is None or email == "":
            test_username = "user" + "_" + str(random.randint(10000000, 99999999))
        else:
            test_username = email.split("@")[0]
    else:
        test_username = auth_username

    # we will try to use the auth_username as the username
    test_user = user_store.get_user_by_name(test_username)
    if test_user is not None:
        # user exists, add an 5 digit random number to the username
        new_username = test_username + "_" + str(random.randint(10000000, 99999999))
    else:
        new_username = test_username

    user_create = UserCreate(
        username=new_username,
        full_name=full_name,
        email=email,
        auth_provider=auth_provider,
        auth_uuid=auth_uuid,
    )
    user = user_store.create_user(user_create)
    return user
