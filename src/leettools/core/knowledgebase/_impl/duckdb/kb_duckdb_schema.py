from dataclasses import dataclass
from typing import Any, Dict

from leettools.core.schemas.knowledgebase import BaseKBSchema


@dataclass
class KBDuckDBSchema(BaseKBSchema):

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """
        Get DuckDB schema definition.
        """
        return cls.get_base_columns()
