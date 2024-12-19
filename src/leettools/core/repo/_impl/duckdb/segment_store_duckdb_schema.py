from dataclasses import dataclass
from typing import Dict

from leettools.core.schemas.segment import BaseSegmentSchema


@dataclass
class SegmentDuckDBSchema(BaseSegmentSchema):
    """DuckDB-specific schema for segment."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
