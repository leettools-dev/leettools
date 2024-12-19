from dataclasses import dataclass
from typing import Any, Dict

from leettools.core.strategy.schemas.strategy import BaseStrategySchema


@dataclass
class StrategyDuckDBSchema(BaseStrategySchema):
    """DuckDB-specific schema for strategy."""

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
