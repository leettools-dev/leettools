from dataclasses import dataclass
from typing import Dict

from leettools.core.strategy.schemas.prompt import BasePromptSchema


@dataclass
class PromptDuckDBSchema(BasePromptSchema):
    """DuckDB-specific schema for prompt."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
