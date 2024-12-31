from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils.obj_utils import add_fieldname_constants


@add_fieldname_constants
class ExtractMetadata(BaseModel):
    """
    Represents information about an extracted database table.
    """

    db_type: str = Field(
        ..., description="The type of the database (e.g., Mysql, Mongo, DuckDB etc)."
    )
    db_uri: str = Field(
        ..., description="The URI used to look up the database access information."
    )
    target_model_name: str = Field(..., description="The name of the target model.")
    target_model_schema_dict: Dict[str, Any] = Field(
        ..., description="The schema dictionary of the target model."
    )
    item_count: int = Field(..., description="The number of items extracted.")
    created_at: datetime = Field(
        ..., description="The timestamp when the extraction was created."
    )
    key_fields: Optional[List[str]] = Field(None, description="The list of key fields.")
    verify_fields: Optional[List[str]] = Field(
        [], description="The list of fields to verify."
    )


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
            ExtractMetadata.FIELD_ITEM_COUNT: "INTEGER",
            ExtractMetadata.FIELD_CREATED_AT: "TIMESTAMP",
            ExtractMetadata.FIELD_KEY_FIELDS: "JSON",
            ExtractMetadata.FIELD_VERIFY_FIELDS: "JSON",
        }
