from dataclasses import dataclass
from typing import Any, Dict

from leettools.eds.usage.schemas.usage_api_call import BaseUsageAPICallSchema


@dataclass
class UsageAPICallDuckDBSchema(BaseUsageAPICallSchema):
    """DuckDB-specific schema for usage api call."""

    TABLE_NAME = "api_call"

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
