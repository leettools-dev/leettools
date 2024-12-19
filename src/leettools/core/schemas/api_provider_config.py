from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar, Dict, List

from pydantic import BaseModel, Field

from leettools.common.utils.obj_utils import add_fieldname_constants


class APIFunction(str, Enum):
    EMBED = "embed"
    RERANK = "rerank"
    INFERENCE = "inference"


class APIEndpointInfo(BaseModel):
    path: str = Field("", description="The path for the endpoint.")
    default_model: str = Field("", description="The default model for the endpoint.")
    supported_models: List[str] = Field(
        [], description="The supported models for the endpoint."
    )


@add_fieldname_constants
class APIProviderConfig(BaseModel):

    api_provider: str = Field(
        ...,
        description="The name for the API provider. Although we only use OpenAI-compatible "
        "API, this field denotes the actual provider.",
    )
    api_key: str = Field(
        ..., description="The API key for the API, use an empty string if not needed."
    )
    base_url: str = Field(
        ...,
        description="The base URL of the API provider, such as https://api.openai.com/v1.",
    )

    endpoints: Dict[APIFunction, APIEndpointInfo] = Field(
        ...,
        description="The endpoints for the API provider. Some API libraries may "
        "need the endpoint to be specified. An existing APIFunction key means that "
        "the API provider supports the function, the value could be an empty string.",
    )


@dataclass
class BaseAPIProviderConfigSchema(ABC):
    TABLE_NAME: ClassVar[str] = "api_provider_config"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        return {
            APIProviderConfig.FIELD_API_PROVIDER: "VARCHAR",
            APIProviderConfig.FIELD_API_KEY: "VARCHAR",
            APIProviderConfig.FIELD_BASE_URL: "VARCHAR",
            APIProviderConfig.FIELD_ENDPOINTS: "VARCHAR",
        }
