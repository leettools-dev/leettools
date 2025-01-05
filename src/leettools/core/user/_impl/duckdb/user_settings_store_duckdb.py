import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.utils import time_utils
from leettools.core.schemas.api_provider_config import (
    APIEndpointInfo,
    APIProviderConfig,
)
from leettools.core.schemas.user import User
from leettools.core.schemas.user_settings import (
    UserSettings,
    UserSettingsCreate,
    UserSettingsItem,
    UserSettingsUpdate,
)
from leettools.core.user._impl.duckdb.api_provider_config_duckdb_schema import (
    APIProviderConfigDuckDBSchema,
)
from leettools.core.user._impl.duckdb.user_settings_duckdb_schema import (
    UserSettingsDuckDBSchema,
)
from leettools.core.user.user_settings_store import AbstractUserSettingsStore
from leettools.settings import SystemSettings


class UserSettingsStoreDuckDB(AbstractUserSettingsStore):
    """
    UserSettingsStoreDuckDB is a UserSettingsStore implementation using DuckDB as the backend.
    """

    def __init__(self, settings: SystemSettings) -> None:
        """
        Initialize the DuckDB PromptStore.
        """
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)

    def _api_provider_config_to_dict(
        self, api_provider_config: APIProviderConfig
    ) -> Dict[str, Any]:
        api_provider_config_dict = api_provider_config.model_dump()
        api_provider_config_dict[APIProviderConfig.FIELD_ENDPOINTS] = json.dumps(
            api_provider_config_dict[APIProviderConfig.FIELD_ENDPOINTS]
        )
        return api_provider_config_dict

    def _dict_to_api_provider_config(
        self, api_provider_config_dict: Dict[str, Any]
    ) -> APIProviderConfig:
        """
        Convert a document to a API provider config.
        """
        if APIProviderConfig.FIELD_ENDPOINTS in api_provider_config_dict:
            api_provider_config_dict[APIProviderConfig.FIELD_ENDPOINTS] = json.loads(
                api_provider_config_dict[APIProviderConfig.FIELD_ENDPOINTS]
            )
            api_provider_config_dict[APIProviderConfig.FIELD_ENDPOINTS] = {
                k: APIEndpointInfo.model_validate(v)
                for k, v in api_provider_config_dict[
                    APIProviderConfig.FIELD_ENDPOINTS
                ].items()
            }
        return APIProviderConfig.model_validate(api_provider_config_dict)

    def _dict_to_user_settings(
        self, user_settings_dict: Dict[str, Any]
    ) -> UserSettings:
        """
        Convert a document to a user settings.
        """
        if UserSettings.FIELD_SETTINGS in user_settings_dict:
            user_settings_dict[UserSettings.FIELD_SETTINGS] = json.loads(
                user_settings_dict[UserSettings.FIELD_SETTINGS]
            )
            for k, v in user_settings_dict[UserSettings.FIELD_SETTINGS].items():
                user_settings_dict[UserSettings.FIELD_SETTINGS][k] = (
                    UserSettingsItem.model_validate(v)
                )
        return UserSettings.model_validate(user_settings_dict)

    def _get_user_settings_table_for_user(self, user_uuid: str) -> str:
        db_name = User.get_user_db_name(user_uuid)
        return self.duckdb_client.create_table_if_not_exists(
            db_name,
            self.settings.COLLECTION_USER_SETTINGS,
            UserSettingsDuckDBSchema.get_schema(),
        )

    def _get_api_provider_config_table_for_user(self, user_uuid: str) -> str:
        db_name = User.get_user_db_name(user_uuid)
        return self.duckdb_client.create_table_if_not_exists(
            db_name,
            self.settings.COLLECTION_API_PROVIDERS,
            APIProviderConfigDuckDBSchema.get_schema(),
        )

    def _save_new_user_settings(
        self, user_settings_create: UserSettingsCreate
    ) -> UserSettings:
        table_name = self._get_user_settings_table_for_user(
            user_settings_create.user_uuid
        )
        user_settings_dict = self._user_settings_to_dict(user_settings_create)
        user_settings_dict[UserSettings.FIELD_USER_SETTINGS_ID] = str(uuid.uuid4())

        current_time = time_utils.current_datetime()
        user_settings_dict[UserSettings.FIELD_CREATED_AT] = current_time
        user_settings_dict[UserSettings.FIELD_UPDATED_AT] = current_time

        column_list = list(user_settings_dict.keys())
        value_list = list(user_settings_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name, column_list=column_list, value_list=value_list
        )
        return self._dict_to_user_settings(user_settings_dict)

    def _update_user_settings(self, user_settings: UserSettings) -> UserSettings:
        table_name = self._get_user_settings_table_for_user(user_settings.user_uuid)

        user_settings_copy = user_settings.model_copy()
        user_settings_copy.updated_at = time_utils.current_datetime()
        user_settings_dict = self._user_settings_to_dict(user_settings_copy)
        user_settings_id = user_settings_dict.pop(UserSettings.FIELD_USER_SETTINGS_ID)
        column_list = list(user_settings_dict.keys())
        value_list = list(user_settings_dict.values())
        where_clause = f"WHERE {UserSettings.FIELD_USER_SETTINGS_ID} = ?"
        value_list = value_list + [user_settings_id]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        user_settings_dict[UserSettings.FIELD_USER_SETTINGS_ID] = user_settings_id
        return self._dict_to_user_settings(user_settings_dict)

    def _update_settings_for_user(
        self, user: User, settings_update: UserSettingsUpdate
    ) -> UserSettings:
        table_name = self._get_user_settings_table_for_user(user.user_uuid)

        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=f"WHERE {UserSettings.FIELD_USER_UUID} = ?",
            value_list=[user.user_uuid],
        )
        if result is None:
            default_setting_items: Dict[str, UserSettingsItem] = (
                self.settings.get_user_configurable_settings()
            )
            default_setting_items.update(settings_update.settings)
            user_settings = UserSettingsCreate(
                user_uuid=user.user_uuid,
                username=user.username,
                settings=default_setting_items,
            )
            return self._save_new_user_settings(user_settings)
        else:
            existing_settings = self._dict_to_user_settings(result)
            existing_settings.settings.update(settings_update.settings)
            return self._update_user_settings(existing_settings)

    def _user_settings_to_dict(self, user_settings: UserSettings) -> Dict[str, Any]:
        user_settings_dict = user_settings.model_dump()
        if UserSettings.FIELD_SETTINGS in user_settings_dict:
            user_settings_dict[UserSettings.FIELD_SETTINGS] = json.dumps(
                user_settings_dict[UserSettings.FIELD_SETTINGS]
            )
        return user_settings_dict

    def add_api_provider_config(
        self, user: User, api_provider_config: APIProviderConfig
    ) -> APIProviderConfig:
        table_name = self._get_api_provider_config_table_for_user(user.user_uuid)

        api_provider_config_dict = self._api_provider_config_to_dict(
            api_provider_config
        )
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=f"WHERE {APIProviderConfig.FIELD_API_PROVIDER} = ?",
            value_list=[api_provider_config.api_provider],
        )
        if result is not None:
            api_provider_id = api_provider_config_dict.pop(
                APIProviderConfig.FIELD_API_PROVIDER
            )
            column_list = list(api_provider_config_dict.keys())
            value_list = list(api_provider_config_dict.values())
            where_clause = f"WHERE {APIProviderConfig.FIELD_API_PROVIDER} = ?"
            value_list = value_list + [api_provider_id]
            self.duckdb_client.update_table(
                table_name=table_name,
                column_list=column_list,
                value_list=value_list,
                where_clause=where_clause,
            )
            api_provider_config_dict[APIProviderConfig.FIELD_API_PROVIDER] = (
                api_provider_id
            )
            return self._dict_to_api_provider_config(api_provider_config_dict)
        else:
            column_list = list(api_provider_config_dict.keys())
            value_list = list(api_provider_config_dict.values())
            self.duckdb_client.insert_into_table(
                table_name=table_name,
                column_list=column_list,
                value_list=value_list,
            )
            return api_provider_config

    def get_all_api_provider_configs_for_user(
        self, user: User
    ) -> List[APIProviderConfig]:
        table_name = self._get_api_provider_config_table_for_user(user.user_uuid)
        result = self.duckdb_client.fetch_all_from_table(table_name=table_name)
        results: List[APIProviderConfig] = []
        for doc in result:
            api_provider_config = self._dict_to_api_provider_config(doc)
            results.append(api_provider_config)
        return results

    def get_api_provider_config_by_name(
        self, user: User, api_provider_name: str
    ) -> APIProviderConfig:
        table_name = self._get_api_provider_config_table_for_user(user.user_uuid)
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=f"WHERE {APIProviderConfig.FIELD_API_PROVIDER} = ?",
            value_list=[api_provider_name],
        )
        if result is not None:
            return self._dict_to_api_provider_config(result)
        else:
            return None

    def get_settings_for_user(self, user: User) -> UserSettings:
        table_name = self._get_user_settings_table_for_user(user.user_uuid)

        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=f"WHERE {UserSettings.FIELD_USER_UUID} = ?",
            value_list=[user.user_uuid],
        )
        if result is None:
            default_setting_items = self.settings.get_user_configurable_settings()
            user_settings_create = UserSettingsCreate(
                user_uuid=user.user_uuid,
                username=user.username,
                settings=default_setting_items,
            )
            return self._save_new_user_settings(user_settings_create)
        else:
            # Update the fields if the default settings have changed.
            default_setting_items = self.settings.get_user_configurable_settings()
            cur_user_settings = self._dict_to_user_settings(result)

            need_update = False
            for key, value in default_setting_items.items():
                if key not in cur_user_settings.settings:
                    cur_user_settings.settings[key] = value
                    need_update = True

            if need_update:
                return self._update_user_settings(cur_user_settings)
            return cur_user_settings

    def update_settings_for_user(
        self, user: User, settings_update: UserSettingsUpdate
    ) -> UserSettings:
        rtn_value = self._update_settings_for_user(user, settings_update)
        return rtn_value

    def _reset_for_test(self, user_uuid: str) -> None:
        assert self.settings.DUCKDB_FILE.endswith("_test.db")
        user_settings_table_name = self._get_user_settings_table_for_user(user_uuid)
        api_provider_config_table_name = self._get_api_provider_config_table_for_user(
            user_uuid
        )
        self.duckdb_client.delete_from_table(table_name=user_settings_table_name)
        self.duckdb_client.delete_from_table(table_name=api_provider_config_table_name)
