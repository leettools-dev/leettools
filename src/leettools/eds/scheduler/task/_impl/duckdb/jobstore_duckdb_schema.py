from dataclasses import dataclass
from typing import Dict

from leettools.eds.scheduler.schemas.job import BaseJobSchema


@dataclass
class JobDuckDBSchema(BaseJobSchema):
    """DuckDB-specific schema for jobs."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
