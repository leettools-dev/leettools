from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.common.utils.obj_utils import add_fieldname_constants


@add_fieldname_constants
class ExtractMetadata(BaseModel):
    """
    Represents information about an extracted database table.

    Attributes:
        db_type (str): The type of the database (e.g., Mysql, Mongo, DuckDB etc).
        db_uri (str): The URI used to look up the database access information.
        target_model_name (str): The name of the target model.
        target_model_schema_dict (Dict[str, Any]): The schema dictionary of the target model.
        key_fields (List[str]): The list of key fields.
        item_count (int): The number of items extracted.
        created_at (datetime): The timestamp when the extraction was created.
        verify_fields (Optional[List[str]]): The list of fields to verify (optional).

    """

    db_type: str
    db_uri: str
    target_model_name: str
    target_model_schema_dict: Dict[str, Any]
    key_fields: List[str]
    item_count: int
    created_at: datetime
    verify_fields: Optional[List[str]] = []


@dataclass
class BaseExtractMetadataSchema(ABC):
    """Abstract base schema for extract metadata."""

    TABLE_NAME: str = "extract_metadata"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, Any]:
        """Get base column definitions shared across implementations."""
        return {
            ExtractMetadata.FIELD_DB_TYPE: "VARCHAR",
            ExtractMetadata.FIELD_DB_URI: "VARCHAR",
            ExtractMetadata.FIELD_TARGET_MODEL_NAME: "VARCHAR",
            ExtractMetadata.FIELD_TARGET_MODEL_SCHEMA_DICT: "VARCHAR",
            ExtractMetadata.FIELD_KEY_FIELDS: "VARCHAR",
            ExtractMetadata.FIELD_ITEM_COUNT: "INTEGER",
            ExtractMetadata.FIELD_CREATED_AT: "TIMESTAMP",
            ExtractMetadata.FIELD_VERIFY_FIELDS: "VARCHAR",
        }
