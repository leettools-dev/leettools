import uuid
from datetime import datetime
from typing import List, Optional

from leettools.common import exceptions
from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.schemas.user import User, UserCreate, UserInDB, UserUpdate
from leettools.core.user._impl.duckdb.user_store_duckdb_schema import UserDuckDBSchema
from leettools.core.user.user_store import AbstractUserStore
from leettools.settings import SystemSettings


class UserStoreDuckDB(AbstractUserStore):
    def __init__(self, settings: SystemSettings) -> None:
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)
        self.table_name = self._get_table_name()
        # TODO: temporarty solution, create an admin user when starts
        admin_user = self.get_user_by_name(User.ADMIN_USERNAME)
        if admin_user is None:
            logger().info(f"Creating the admin user {User.ADMIN_USERNAME}")
            admin_user = self.create_user(UserCreate(username=User.ADMIN_USERNAME))

    def _get_table_name(self) -> str:
        return self.duckdb_client.create_table_if_not_exists(
            schema_name=self.settings.DB_COMMOM,
            table_name=self.settings.COLLECTION_USERS,
            columns=UserDuckDBSchema.get_schema(),
        )

    def change_user_balance(self, user_uuid: str, balance_change: int) -> User:
        user = self.get_user_by_uuid(user_uuid)
        if user is None:
            raise exceptions.EntityNotFoundException(
                entity_name=user_uuid,
                entity_type="User",
            )
        if user.balance is None:
            user.balance = 0
        user.balance += balance_change

        column_list = [User.FIELD_BALANCE]
        value_list = [user.balance, user_uuid]
        where_clause = f"WHERE {User.FIELD_USER_UUID} = ?"
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_user_by_uuid(user_uuid)

    def create_user(self, user_create: UserCreate) -> Optional[User]:
        from leettools.context_manager import Context, ContextManager

        context = ContextManager().get_context()  # type: Context
        if context.is_test:
            if (
                not user_create.username.startswith(User.TEST_USERNAME_PREFIX)
                and user_create.username != User.ADMIN_USERNAME
            ):
                raise exceptions.InvalidValueException(
                    name="user.username",
                    expected=f"staring with {User.TEST_USERNAME_PREFIX}",
                    actual=user_create.username,
                )

        user_in_db = UserInDB.from_user_create(user_create)
        user_dict = user_in_db.model_dump()
        user_dict[User.FIELD_USER_UUID] = str(uuid.uuid4())
        column_list = list(user_dict.keys())
        value_list = list(user_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return User.from_user_in_db(UserInDB.model_validate(user_dict))

    def delete_user_by_id(self, user_uuid: str) -> bool:
        logger().info(f"Deleting user {user_uuid}")
        where_clause = f"WHERE {User.FIELD_USER_UUID} = ?"
        value_list = [user_uuid]
        self.duckdb_client.delete_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        # TODO: we should make api_key scrambled in the database
        # here we should only check the scrambled value
        where_clause = f"WHERE {User.FIELD_API_KEY} = ?"
        value_list = [api_key]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is not None:
            return User.from_user_in_db(UserInDB.model_validate(result))
        else:
            return None

    def get_user_by_auth_uuid(
        self, auth_provider: str, auth_uuid: str
    ) -> Optional[User]:
        where_clause = (
            f"WHERE {User.FIELD_AUTH_PROVIDER} = ? AND {User.FIELD_AUTH_UUID} = ?"
        )
        value_list = [auth_provider, auth_uuid]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is not None:
            return User.from_user_in_db(UserInDB.model_validate(result))
        else:
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        where_clause = f"WHERE {User.FIELD_EMAIL} = ?"
        value_list = [email]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is not None:
            return User.from_user_in_db(UserInDB.model_validate(result))
        else:
            return None

    def get_user_by_name(self, username: str) -> Optional[User]:
        where_clause = f"WHERE {User.FIELD_USERNAME} = ?"
        value_list = [username]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is not None:
            return User.from_user_in_db(UserInDB.model_validate(result))
        else:
            return None

    def get_user_by_uuid(self, user_uuid: str) -> Optional[User]:
        where_clause = f"WHERE {User.FIELD_USER_UUID} = ?"
        value_list = [user_uuid]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is not None:
            return User.from_user_in_db(UserInDB.model_validate(result))
        else:
            return None

    def get_users(self) -> List[User]:
        result = self.duckdb_client.fetch_all_from_table(
            table_name=self.table_name,
        )
        rtn_list = []
        for user_dict in result:
            rtn_list.append(User.from_user_in_db(UserInDB.model_validate(user_dict)))
        return rtn_list

    def update_user(self, user_update: UserUpdate) -> Optional[User]:
        user_uuid = user_update.user_uuid
        update_dict = user_update.model_dump()
        update_dict[User.FIELD_UPDATED_AT] = time_utils.current_datetime()
        user_uuid = update_dict.pop(User.FIELD_USER_UUID)
        column_list = list(update_dict.keys())
        where_clause = f"WHERE {User.FIELD_USER_UUID} = ?"
        value_list = list(update_dict.values()) + [user_uuid]
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_user_by_uuid(user_uuid)

    def _reset_for_test(self) -> None:
        assert self.settings.DUCKDB_FILE.endswith("_test.db")
        self.duckdb_client.delete_from_table(table_name=self.table_name)
        self.create_user(UserCreate(username=User.ADMIN_USERNAME))

    def _get_dbname_for_test(self) -> str:
        return self.settings.DB_COMMOM
