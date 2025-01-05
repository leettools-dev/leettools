import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, get_args, get_origin

from pydantic import BaseModel, Field

from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import TypeVar_BaseModel


def pydantic_to_duckdb_schema(pydantic_model: TypeVar_BaseModel) -> Dict[str, str]:
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

        def base_pydantic_type_to_duckdb(origin, field_type) -> str:
            if origin is list:
                duckdb_type = "JSON"  # Lists are represented as JSON in DuckDB
            elif origin is dict:
                duckdb_type = "JSON"  # Dicts are represented as JSON in DuckDB
            elif "str" in str(field_type).lower():
                duckdb_type = "VARCHAR"
            elif "int" in str(field_type).lower():
                if "_in_ms" in field_name.lower():
                    duckdb_type = "UINT64"  # hack to handle millisecond timestamps
                else:
                    duckdb_type = "INTEGER"
            elif "float" in str(field_type).lower():
                duckdb_type = "DOUBLE"
            elif "bool" in str(field_type).lower():
                duckdb_type = "BOOLEAN"
            elif "datetime" in str(field_type).lower():
                duckdb_type = "TIMESTAMP"
            else:
                duckdb_type = "VARCHAR"  # Default to VARCHAR
            return duckdb_type

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
                pydantic_type_name = args[0].__name__
                duckdb_type = base_pydantic_type_to_duckdb(origin, pydantic_type_name)
        else:
            duckdb_type = base_pydantic_type_to_duckdb(origin, field_type)

        # Append PRIMARY KEY if the field is marked as primary key
        if field_metadata.get("primary_key", False):
            duckdb_type += " PRIMARY KEY"

        duckdb_fields[field_name] = duckdb_type

    return duckdb_fields


def duckdb_data_to_pydantic_obj(
    data: Dict[str, Any], pydantic_model: TypeVar_BaseModel
) -> BaseModel:
    """
    Check the field type of each key in the data and convert the value to the appropriate type.
    Then use model_validate() to create a Pydantic object.

    Args:
    - data (Dict[str, Any]): The data to convert.
    - pydantic_model (TypeVar_BaseModel): The Pydantic model to use.
    """
    for key, value in data.items():
        field_info = pydantic_model.model_fields.get(key)
        if field_info is None:
            logger().warning(f"Field {key} not found in Pydantic model")
            continue

        field_type = field_info.annotation
        origin = get_origin(field_type)
        args = get_args(field_type)

        # print(
        #     f"field_name: {key}, field_type: {field_type}, origin: {origin}, args: {args}"
        # )

        def base_type_conversion(field_type, value):
            if "list" in str(field_type).lower():
                data[key] = json.loads(value)
            elif "dict" in str(field_type).lower():
                data[key] = json.loads(value)
            elif "str" in str(field_type).lower():
                data[key] = str(value)
            elif "uint64" in str(field_type).lower():
                data[key] = int(value)
            elif "int" in str(field_type).lower():
                data[key] = int(value)
            elif "float" in str(field_type).lower():
                data[key] = float(value)
            elif "bool" in str(field_type).lower():
                data[key] = bool(value)
            elif "datetime" in str(field_type).lower():
                if type(value) is str:
                    data[key] = time_utils.datetime_from_timestamp_in_ms()
                elif type(value) is datetime:
                    data[key] = value
                else:
                    logger().warning(f"Unknown datetime format: {value}")
                    data[key] = value
            else:
                logger().warning(f"Unknown field type: {field_type}, using string")
                data[key] = str(value)

        if origin is Union:
            # Check if one of the types is NoneType (Optional)
            real_args = [arg for arg in args if arg is not type(None)]
            types = [str(arg).lower() for arg in real_args]
            if any("list" in t or "dict" in t for t in types):
                data[key] = json.loads(value)
            else:
                if len(types) > 1:
                    logger().warning(
                        f"Union type with multiple types not supported: {field_type}"
                    )
                pydantic_type = real_args[0]
                base_type_conversion(pydantic_type, value)
        else:
            base_type_conversion(field_type, value)

    return pydantic_model.model_validate(data)


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
