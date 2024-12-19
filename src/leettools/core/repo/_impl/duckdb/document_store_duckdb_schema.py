from dataclasses import dataclass
from typing import Dict

from leettools.core.schemas.document import BaseDocumentSchema


@dataclass
class DocumentDuckDBSchema(BaseDocumentSchema):
    """DuckDB-specific schema for document."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
