from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.common.utils.obj_utils import add_fieldname_constants

API_CALL_ENDPOINT_COMPLETION = "completion"
API_CALL_ENDPOINT_EMBED = "embed"


class UsageAPICallCreate(BaseModel):
    user_uuid: str
    api_provider: str
    target_model_name: str
    endpoint: str
    success: bool
    total_token_count: int
    start_timestamp_in_ms: int
    end_timestamp_in_ms: int
    is_batch: Optional[bool] = False
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    call_target: Optional[str] = None
    input_token_count: Optional[int] = -1
    output_token_count: Optional[int] = -1


@add_fieldname_constants
class UsageAPICall(UsageAPICallCreate):
    usage_record_id: str
    input_leet_token_count: Optional[int] = -1
    output_leet_token_count: Optional[int] = -1
    created_at: datetime


# TODO: right now we do not separate batch and non-batch calls
# although we added the is_batch field in the UsageAPICallCreate model


@dataclass
class BaseUsageAPICallSchema(ABC):
    """Abstract base schema for usage api call implementations."""

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> List[str]:
        """Get base column definitions shared across implementations."""
        return {
            UsageAPICall.FIELD_USER_UUID: "VARCHAR",
            UsageAPICall.FIELD_API_PROVIDER: "VARCHAR",
            UsageAPICall.FIELD_TARGET_MODEL_NAME: "VARCHAR",
            UsageAPICall.FIELD_ENDPOINT: "VARCHAR",
            UsageAPICall.FIELD_SUCCESS: "BOOLEAN",
            UsageAPICall.FIELD_TOTAL_TOKEN_COUNT: "INTEGER",
            UsageAPICall.FIELD_START_TIMESTAMP_IN_MS: "BIGINT",
            UsageAPICall.FIELD_END_TIMESTAMP_IN_MS: "BIGINT",
            UsageAPICall.FIELD_IS_BATCH: "BOOLEAN",
            UsageAPICall.FIELD_SYSTEM_PROMPT: "VARCHAR",
            UsageAPICall.FIELD_USER_PROMPT: "VARCHAR",
            UsageAPICall.FIELD_CALL_TARGET: "VARCHAR",
            UsageAPICall.FIELD_INPUT_TOKEN_COUNT: "INTEGER",
            UsageAPICall.FIELD_OUTPUT_TOKEN_COUNT: "INTEGER",
            UsageAPICall.FIELD_USAGE_RECORD_ID: "VARCHAR PRIMARY KEY",
            UsageAPICall.FIELD_INPUT_LEET_TOKEN_COUNT: "INTEGER",
            UsageAPICall.FIELD_OUTPUT_LEET_TOKEN_COUNT: "INTEGER",
            UsageAPICall.FIELD_CREATED_AT: "TIMESTAMP",
        }


class TokenType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class UsageModelSummary(BaseModel):
    token_by_type: Dict[TokenType, int]
    leet_token_by_type: Dict[TokenType, int]
    # the first key is the endpoint, the second key is the token type
    token_by_endpoint: Dict[str, Dict[TokenType, int]]
    leet_token_by_endpoint: Dict[str, Dict[TokenType, int]]


class UsageAPIProviderSummary(BaseModel):
    token_by_type: Dict[TokenType, int]
    leet_token_by_type: Dict[TokenType, int]
    # the key is the model name
    usage_by_model: Dict[str, UsageModelSummary]


class UsageAPICallSummary(BaseModel):
    # type is "input" or "output"
    token_by_type: Dict[TokenType, int]
    leet_token_by_type: Dict[TokenType, int]
    # the key is the provider name
    usage_by_provider: Dict[str, UsageAPIProviderSummary]
