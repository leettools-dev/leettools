from dataclasses import dataclass
from typing import Any, Dict

from leettools.eds.metadata.schemas.kb_metadata import BaseKBMetadataSchema


@dataclass
class DuckDBKBMetadataSchema(BaseKBMetadataSchema):
    """DuckDB-specific schema for KB metadata."""

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return cls.get_base_columns()
