from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, Field

from leettools.common.logging import logger
from leettools.common.utils.config_utils import value_to_bool
from leettools.common.utils.obj_utils import add_fieldname_constants


class UserSettingsItem(BaseModel):

    section: str = Field(..., description="The section of the settings")
    name: str = Field(..., description="The name of the variable.")
    description: Optional[str] = Field(
        None, description="The description of the variable."
    )
    default_value: Optional[str] = Field(
        None, description="The default value of the variable."
    )
    value: Optional[str] = Field(None, description="The value of the variable.")
    value_type: Optional[str] = Field(
        "str",
        description="The type of the value," "currently support str, int, float, bool.",
    )


"""
See [README](./README.md) about the usage of different pydantic models.
"""


class UserSettingsCreate(BaseModel):
    # we use user_uuid to indentify the user, the user_name is just for display
    user_uuid: str = Field(..., description="The uuid of the user.")
    username: Optional[str] = Field(None, description="The name of the user.")
    settings: Dict[str, UserSettingsItem] = Field(
        ..., description="The settings of the user, the key is the name of the setting."
    )


class UserSettingsUpdate(UserSettingsCreate):
    pass


@add_fieldname_constants
class UserSettings(UserSettingsCreate):
    """
    The settings that can be set by the user.
    """

    user_settings_id: str = Field(..., description="The id of the user settings.")
    created_at: Optional[datetime] = Field(
        None, description="The time the settings was created."
    )
    updated_at: Optional[datetime] = Field(
        None, description="The time the settings was updated."
    )

    def get_value(self, key: str, default_value: Any) -> Optional[Any]:
        setting_item: UserSettingsItem = self.settings.get(key)
        if setting_item is None:
            return default_value
        value = setting_item.value
        if value is None:
            value = setting_item.default_value

        if setting_item.value_type == "int":
            try:
                return_value = int(value)
            except ValueError:
                return default_value
            return return_value

        if setting_item.value_type == "float":
            try:
                return_value = float(value)
            except ValueError:
                return default_value
            return return_value

        if setting_item.value_type == "bool":
            return value_to_bool(value)

        if setting_item.value_type == "str":
            return value

        logger().warning(
            f"Unsupported value type {setting_item.value_type} for key {key}"
        )
        return value


@dataclass
class BaseUserSettingsSchema(ABC):
    TABLE_NAME: ClassVar[str] = "user_settings"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        return {
            UserSettings.FIELD_USER_UUID: "VARCHAR",
            UserSettings.FIELD_USERNAME: "VARCHAR",
            UserSettings.FIELD_SETTINGS: "VARCHAR",
            UserSettings.FIELD_USER_SETTINGS_ID: "VARCHAR PRIMARY KEY",
            UserSettings.FIELD_CREATED_AT: "TIMESTAMP",
            UserSettings.FIELD_UPDATED_AT: "TIMESTAMP",
        }
