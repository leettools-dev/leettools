from dataclasses import dataclass
from typing import Dict

from leettools.eds.scheduler.schemas.task import BaseTaskSchema


@dataclass
class TaskDuckDBSchema(BaseTaskSchema):
    """DuckDB-specific schema for tasks."""

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        """Get DuckDB column definitions."""
        return cls.get_base_columns()
