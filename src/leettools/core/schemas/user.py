from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import auth_utils, time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties
from leettools.core.consts.accouting import INIT_BALANCE

"""
See [README](./README.md) about the usage of different pydantic models.
"""


class UserBase(BaseModel):
    username: str = Field(..., description="The unique username of the user.")
    full_name: Optional[str] = Field(None, description="The full name of the user.")
    email: Optional[str] = Field(None, description="The email of the user.")
    disabled: Optional[bool] = Field(None, description="Whether the user is disabled.")


class UserCreate(UserBase):
    auth_provider: Optional[str] = Field(None, description="The auth provider.")
    auth_username: Optional[str] = Field(None, description="The auth username.")
    auth_uuid: Optional[str] = Field(None, description="The auth UUID.")


class UserUpdate(UserBase):
    # we do not allow to change the auth information for now
    user_uuid: str = Field(..., description="The uuid of the user.")


class UserInDB(UserCreate):

    user_uuid: str = Field(..., description="The uuid of the user.")
    # balance will be updated through specific API
    balance: Optional[int] = Field(None, description="The balance of the user.")
    created_at: Optional[datetime] = Field(
        None, description="The time the user was created."
    )
    updated_at: Optional[datetime] = Field(
        None, description="The time the user was updated."
    )
    api_key: Optional[str] = Field(
        None,
        description="The API Key assigned to the user, right now one for each user.",
    )

    @classmethod
    def from_user_create(UserInDB, user_create: UserCreate) -> "UserInDB":
        ct = time_utils.current_datetime()
        user_in_db = UserInDB(
            username=user_create.username,
            user_uuid="",
            balance=INIT_BALANCE,
            created_at=ct,
            updated_at=ct,
            api_key=auth_utils.generate_api_key(),
        )
        assign_properties(user_create, user_in_db)
        return user_in_db


@add_fieldname_constants
class User(UserInDB):
    """
    This class represents a user entry used by the client
    """

    USER_ID_ATTR: ClassVar[str] = "user_uuid"

    # this user will be created automatically when starting the service
    ADMIN_USERNAME: ClassVar[str] = "admin"
    TEST_USERNAME_PREFIX: ClassVar[str] = "test_user"

    @classmethod
    def get_admin_user(cls) -> "User":
        from leettools.context_manager import Context, ContextManager

        context = ContextManager().get_context()  # type: Context
        user_store = context.get_user_store()
        admin_user = user_store.get_user_by_name(cls.ADMIN_USERNAME)
        return admin_user

    @classmethod
    def get_user_db_name(cls, user_uuid: str) -> str:
        from leettools.context_manager import Context, ContextManager

        context = ContextManager().get_context()  # type: Context
        if context.is_test:
            return f"test_user_{user_uuid}"
        else:
            return f"user_{user_uuid}"

    @classmethod
    def from_user_in_db(User, user_in_db: UserInDB) -> "User":
        user = User(
            username=user_in_db.username,
            user_uuid=user_in_db.user_uuid,
        )
        assign_properties(user_in_db, user)
        return user


@dataclass
class BaseUserSchema(ABC):
    TABLE_NAME: ClassVar[str] = "user"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        return {
            User.FIELD_USER_UUID: "VARCHAR PRIMARY KEY",
            User.FIELD_USERNAME: "VARCHAR",
            User.FIELD_FULL_NAME: "VARCHAR",
            User.FIELD_EMAIL: "VARCHAR",
            User.FIELD_DISABLED: "BOOLEAN",
            User.FIELD_AUTH_PROVIDER: "VARCHAR",
            User.FIELD_AUTH_USERNAME: "VARCHAR",
            User.FIELD_AUTH_UUID: "VARCHAR",
            User.FIELD_BALANCE: "INTEGER",
            User.FIELD_API_KEY: "VARCHAR",
            User.FIELD_CREATED_AT: "TIMESTAMP",
            User.FIELD_UPDATED_AT: "TIMESTAMP",
        }
