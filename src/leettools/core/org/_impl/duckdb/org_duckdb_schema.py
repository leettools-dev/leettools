from dataclasses import dataclass
from typing import Any, Dict

from leettools.core.schemas.organization import BaseOrgSchema


@dataclass
class OrgDuckDBSchema(BaseOrgSchema):
    """DuckDB-specific schema for org."""

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
