from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils.obj_utils import add_fieldname_constants

"""
A prompt that user can use to inference with the model. It is defined as a string 
template with a list of optional variables. The prompt is immutable after creation. 
The user can override the default value of the variables when using the prompt.
"""


class PromptStatus(str, Enum):
    """
    The status of the prompt. We can't delete a prompt because we need to keep the
    record.
    """

    PRODUCTION = "production"
    EXPERIMENT = "experiment"
    DISABLED = "diabled"


class PromptCategory(str, Enum):
    """
    We use prompts in different scenarios, so we need to categorize them
    """

    INTENTION = "intention"
    REWRITE = "rewrite"
    INFERENCE = "inference"
    ENTITY = "entity"
    REPORT = "report"
    COMPLETION = "completion"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    PLANNING = "planning"
    WRITING = "writing"


class PromptType(str, Enum):
    """
    OpenAI API has three types of prompts:
    * system: set up the guidance of the LLM
    * assistant: the context from previous conversation
    * user: the actual user query
    """

    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


class PromptBase(BaseModel):
    """
    A prompt template that user can use to inference with the model
    """

    prompt_category: PromptCategory = Field(
        ..., description="The category of the prompt"
    )
    prompt_type: PromptType = Field(
        PromptType.SYSTEM, description="The type of the prompt"
    )
    prompt_template: str = Field(..., description="The prompt template")
    prompt_variables: Optional[Dict[str, Any]] = Field(
        None,
        description="The variables used in the prompt template. The value should"
        "be the default value of the variable, but is currently unused.",
    )


class PromptCreate(PromptBase):
    pass


@add_fieldname_constants
class Prompt(PromptBase):
    prompt_id: str = Field(..., description="The unique identifier of the prompt")
    prompt_hash: str = Field(..., description="The hash of the prompt template")
    prompt_status: str = Field(
        PromptStatus.PRODUCTION, description="The status of the prompt."
    )
    created_at: Optional[datetime] = Field(
        None, description="The creation time of the prompt"
    )
    updated_at: Optional[datetime] = Field(
        None, description="The last update time of the prompt"
    )


@dataclass
class BasePromptSchema(ABC):
    """Abstract base schema for prompt implementations."""

    TABLE_NAME: str = "prompts"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        """Get base column definitions shared across implementations."""
        return {
            Prompt.FIELD_PROMPT_CATEGORY: "VARCHAR",
            Prompt.FIELD_PROMPT_TYPE: "VARCHAR",
            Prompt.FIELD_PROMPT_TEMPLATE: "VARCHAR",
            Prompt.FIELD_PROMPT_VARIABLES: "VARCHAR",
            Prompt.FIELD_PROMPT_ID: "VARCHAR PRIMARY KEY",
            Prompt.FIELD_PROMPT_HASH: "VARCHAR",
            Prompt.FIELD_PROMPT_STATUS: "VARCHAR",
            Prompt.FIELD_CREATED_AT: "TIMESTAMP",
            Prompt.FIELD_UPDATED_AT: "TIMESTAMP",
        }
