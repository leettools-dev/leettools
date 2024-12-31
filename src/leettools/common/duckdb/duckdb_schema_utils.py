from datetime import datetime
from typing import Any, Dict, List, Optional, Union, get_args, get_origin

from pydantic import BaseModel, Field

from leettools.common.logging import logger


def pydantic_to_duckdb_schema(pydantic_model: BaseModel) -> Dict[str, str]:
    """
    Converts a Pydantic model into a DuckDB schema representation as a simple dictionary.

    Args:
    - pydantic_model (BaseModel): The Pydantic model to convert.

    Returns:
    - Dict[str, str]: Dictionary mapping field names to DuckDB types with PRIMARY KEY for primary keys.
    """
    duckdb_fields = {}

    for field_name, field_info in pydantic_model.model_fields.items():
        field_type = field_info.annotation
        field_metadata = field_info.json_schema_extra or {}

        # Handle Union types
        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is Union:
            # Check if one of the types is NoneType (Optional)
            types = [str(arg).lower() for arg in args if arg is not type(None)]
            if any("list" in t or "dict" in t for t in types):
                duckdb_type = "JSON"
            else:
                if len(types) > 1:
                    logger().warning(
                        f"Union type with multiple types not supported: {field_type}"
                    )
                duckdb_type = args[0].__name__.upper()
                if duckdb_type == "DATETIME":
                    duckdb_type = "TIMESTAMP"
        elif origin is list:
            duckdb_type = "JSON"  # Lists are represented as JSON in DuckDB
        elif origin is dict:
            duckdb_type = "JSON"  # Dicts are represented as JSON in DuckDB
        elif "str" in str(field_type).lower():
            duckdb_type = "VARCHAR"
        elif "int" in str(field_type).lower():
            duckdb_type = "INTEGER"
        elif "float" in str(field_type).lower():
            duckdb_type = "DOUBLE"
        elif "bool" in str(field_type).lower():
            duckdb_type = "BOOLEAN"
        elif "datetime" in str(field_type).lower():
            duckdb_type = "TIMESTAMP"
        else:
            duckdb_type = "VARCHAR"  # Default to VARCHAR

        # Append PRIMARY KEY if the field is marked as primary key
        if field_metadata.get("primary_key", False):
            duckdb_type += " PRIMARY KEY"

        duckdb_fields[field_name] = duckdb_type

    return duckdb_fields


if __name__ == "__main__":

    # Example Pydantic model
    class ExampleModel(BaseModel):
        name: str = Field(..., json_schema_extra={"primary_key": True})
        age: int
        height: Optional[float]
        email: Union[str, None] = Field(None, json_schema_extra={"index": True})
        active: bool
        metadata: Dict[str, Any]
        aliases: Optional[List[str]]
        created_at: Optional[datetime]

    # Convert to DuckDB schema
    duckdb_schema = pydantic_to_duckdb_schema(ExampleModel)
    print("\nDuckDB Schema:")
    print(duckdb_schema)
