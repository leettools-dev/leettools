from dataclasses import dataclass
from typing import Any, Dict

from leettools.core.schemas.user import BaseUserSchema


@dataclass
class UserDuckDBSchema(BaseUserSchema):
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """
        Get DuckDB schema definition.
        """
        return cls.get_base_columns()
