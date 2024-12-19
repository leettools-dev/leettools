from dataclasses import dataclass
from typing import Dict

from leettools.core.schemas.docsink import BaseDocsinkSchema


@dataclass
class DocsinkDuckDBSchema(BaseDocsinkSchema):
    """DuckDB-specific schema for docsink."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
