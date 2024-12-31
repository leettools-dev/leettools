from dataclasses import dataclass
from typing import Any, Dict

from leettools.flow.schemas.extract_metadata import BaseExtractMetadataSchema


@dataclass
class DuckDBExtractMetadataSchema(BaseExtractMetadataSchema):
    """DuckDB-specific schema for extract metadata."""

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
