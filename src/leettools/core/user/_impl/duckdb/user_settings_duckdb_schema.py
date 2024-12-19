from dataclasses import dataclass
from typing import Any, Dict

from leettools.core.schemas.user_settings import BaseUserSettingsSchema


@dataclass
class UserSettingsDuckDBSchema(BaseUserSettingsSchema):
    """
    DuckDB schema definition for user settings.
    """

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
