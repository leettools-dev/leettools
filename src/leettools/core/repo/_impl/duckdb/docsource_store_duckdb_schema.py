from dataclasses import dataclass
from typing import Dict

from leettools.core.schemas.docsource import BaseDocSourceSchema


@dataclass
class DocSourceDuckDBSchema(BaseDocSourceSchema):
    """DuckDB-specific schema for docsource."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
