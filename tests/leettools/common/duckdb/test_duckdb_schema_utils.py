from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from leettools.common.duckdb.duckdb_schema_utils import pydantic_to_duckdb_schema


def test_pydantic_to_duckdb_schema():

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

    target_schema = {
        "name": "VARCHAR PRIMARY KEY",
        "age": "INTEGER",
        "height": "DOUBLE",
        "email": "VARCHAR",
        "active": "BOOLEAN",
        "metadata": "JSON",
        "aliases": "JSON",
        "created_at": "TIMESTAMP",
    }
    assert duckdb_schema == target_schema
