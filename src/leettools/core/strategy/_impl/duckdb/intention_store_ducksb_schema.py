from dataclasses import dataclass
from typing import Any, Dict

from leettools.core.strategy.schemas.intention import BaseIntentionSchema


@dataclass
class IntentionDuckDBSchema(BaseIntentionSchema):
    """DuckDB-specific schema for intention."""

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
