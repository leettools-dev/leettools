from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, Field

from leettools.common.exceptions import UnexpectedCaseException
from leettools.common.utils.obj_utils import add_fieldname_constants
from leettools.core.strategy.schemas.strategy_conf import StrategyConfCreate
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.core.strategy.schemas.strategy_status import StrategyStatus

"""
The Strategy class contains all the dynamic configurations for a Flow, required by
the Executor that runs the flow. A Flow is a program of Steps, each of which is an LLM 
API call or similar tool execution function.

Each Strategy object contains a dictionary of StrategySection objects, the key is
the step name, and the value is the StrategySection object that contains the configuration
for the step.

Since we will allow to add new types of steps in the future, we will not use a predefined
StepName enum here. Instead, we will use a string as the key in the dictionary.

We allow user to change the configurations of each Step, so each customized Strategy object
will be stored in the database for future verification and usage.
"""


class StrategyBase(BaseModel):

    # The key is the step name, for example, "intention", "rewrite", "search", "rerank"
    # The value is the StrategySection object that has the information needed for the step.
    # When we add a new step, we need to add a new StrategySection object to the dictionary.
    # Usually the default section contains the LLM API call info, but search / rerank
    # steps need other information.
    strategy_sections: Optional[Dict[str, StrategySection]] = None


class StrategyCreate(StrategyBase):
    strategy_name: str = Field(
        ..., description="The strategy name, unique for the user."
    )

    strategy_description: Optional[str] = Field(
        None, description="The strategy description."
    )

    user_uuid: Optional[str] = Field(
        None, description="The owner's user_uuid. If None, it is a system strategy."
    )


@add_fieldname_constants
class Strategy(StrategyCreate):

    DYNAMIC_STRATEGY_ID: ClassVar[str] = "-1"

    @classmethod
    def get_dynamic_strategy(cls, strategy_base: StrategyBase) -> "Strategy":
        return Strategy(
            strategy_id=Strategy.DYNAMIC_STRATEGY_ID,
            strategy_sections=strategy_base.strategy_sections,
            strategy_name="",
            strategy_hash="",
            strategy_version="",
            strategy_status=StrategyStatus.ACTIVE.value,
            is_system=False,
        )

    strategy_id: str = Field(..., description="The strategy id")
    strategy_hash: str = Field(..., description="The hash of the strategy")
    strategy_version: str = Field(
        ..., description="The version of the strategy using a timestamp"
    )
    strategy_status: str = Field(
        StrategyStatus.ACTIVE.value, description="The strategy status"
    )
    is_system: bool = Field(
        False, description="Whether the strategy is a system strategy or not"
    )
    created_at: Optional[datetime] = Field(None, description="The creation time")
    updated_at: Optional[datetime] = Field(None, description="The last update time")

    def get_display_name(self) -> str:
        if self.strategy_name is not None and self.strategy_name != "":
            return self.strategy_name
        if self.strategy_id != Strategy.DYNAMIC_STRATEGY_ID:
            raise UnexpectedCaseException(
                f"strategy_id is not {Strategy.DYNAMIC_STRATEGY_ID} but strategy_name is None"
            )
        return "Customized"


"""
Originally the strategy was created from a single JSON file and loaded into the 
StrategyConfCreate object. After we create the Strategy object, we reused the JSON file
format and convert that into the Strategy object here.
"""


def convert_strategy_conf_create(
    strategy_conf_create: StrategyConfCreate,
) -> StrategyCreate:

    if strategy_conf_create.intention_options is not None:
        intention_model_name = strategy_conf_create.intention_options.get(
            "model_name", None
        )
    else:
        intention_model_name = None

    intention_section = StrategySection(
        section_name=StrategySectionName.INTENTION,
        strategy_name=strategy_conf_create.intention,
        strategy_options=strategy_conf_create.intention_options,
        api_model_name=intention_model_name,
        intention_list=strategy_conf_create.intention_list,
        llm_system_prompt_id=strategy_conf_create.intention_sp_id,
        llm_user_prompt_id=strategy_conf_create.intention_up_id,
    )

    if strategy_conf_create.rewrite_options is not None:
        rewrite_model_name = strategy_conf_create.rewrite_options.get(
            "model_name", None
        )
    else:
        rewrite_model_name = None

    rewrite_section = StrategySection(
        section_name=StrategySectionName.REWRITE,
        strategy_name=strategy_conf_create.rewrite,
        strategy_options=strategy_conf_create.rewrite_options,
        api_model_name=rewrite_model_name,
        intention_list=strategy_conf_create.intention_list,
        llm_system_prompt_ids_by_intention=strategy_conf_create.rewrite_sp_ids,
        llm_user_prompt_ids_by_intention=strategy_conf_create.rewrite_up_ids,
    )

    search_section = StrategySection(
        section_name=StrategySectionName.SEARCH,
        strategy_name=strategy_conf_create.search,
        strategy_options=strategy_conf_create.search_options,
    )

    if strategy_conf_create.rerank_options is not None:
        rerank_model_name = strategy_conf_create.rerank_options.get("model_name", None)
    else:
        rerank_model_name = None

    rerank_section = StrategySection(
        section_name=StrategySectionName.RERANK,
        strategy_name=strategy_conf_create.rerank,
        api_model_name=rerank_model_name,
        strategy_options=strategy_conf_create.rerank_options,
    )

    context_section_display = StrategySection(
        section_name=StrategySectionName.CONTEXT,
        strategy_name="default",
        strategy_options={
            "enable_neighboring_context": strategy_conf_create.enable_neighboring_context
        },
    )

    inference_section_display = StrategySection(
        section_name=StrategySectionName.INFERENCE,
        strategy_name="default",
        strategy_options={},
        api_model_name=strategy_conf_create.target_model_name,
        intention_list=strategy_conf_create.intention_list,
        llm_system_prompt_ids_by_intention=strategy_conf_create.system_prompt_ids,
        llm_user_prompt_ids_by_intention=strategy_conf_create.user_prompt_ids,
    )

    general_section_display = StrategySection(
        section_name=StrategySectionName.GENERAL,
        strategy_name="default",
        strategy_options={"keep_query_lanaugage": True},
    )

    return StrategyCreate(
        strategy_name=strategy_conf_create.strategy_name,
        strategy_description=strategy_conf_create.strategy_description,
        strategy_sections={
            StrategySectionName.INTENTION: intention_section,
            StrategySectionName.REWRITE: rewrite_section,
            StrategySectionName.SEARCH: search_section,
            StrategySectionName.RERANK: rerank_section,
            StrategySectionName.CONTEXT: context_section_display,
            StrategySectionName.INFERENCE: inference_section_display,
            StrategySectionName.GENERAL: general_section_display,
        },
    )


@dataclass
class BaseStrategySchema(ABC):
    """Abstract base schema for strategy implementations."""

    TABLE_NAME: ClassVar[str] = "strategy"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""
        pass

    @classmethod
    @abstractmethod
    def get_base_columns(cls) -> Dict[str, str]:
        """Get base column definitions shared across implementations."""
        return {
            Strategy.FIELD_STRATEGY_SECTIONS: "VARCHAR",
            Strategy.FIELD_STRATEGY_NAME: "VARCHAR",
            Strategy.FIELD_STRATEGY_DESCRIPTION: "VARCHAR",
            Strategy.FIELD_USER_UUID: "VARCHAR",
            Strategy.FIELD_STRATEGY_ID: "VARCHAR PRIMARY KEY",
            Strategy.FIELD_STRATEGY_HASH: "VARCHAR",
            Strategy.FIELD_STRATEGY_VERSION: "VARCHAR",
            Strategy.FIELD_STRATEGY_STATUS: "VARCHAR",
            Strategy.FIELD_IS_SYSTEM: "BOOLEAN",
            Strategy.FIELD_CREATED_AT: "TIMESTAMP",
            Strategy.FIELD_UPDATED_AT: "TIMESTAMP",
        }
