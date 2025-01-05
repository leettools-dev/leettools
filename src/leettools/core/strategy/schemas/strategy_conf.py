from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.core.strategy.schemas.strategy_status import StrategyStatus

SEARCH_OPTION_TOP_K = "top_k_for_search"
SEARCH_OPTION_METRIC = "dense_search_metric"

"""
This class is the original raw conf format for users to specify the strategy in a single
JSON file. We then convert it to the Strategy class for storage and usage.
"""


class StrategyConfBase(BaseModel):
    """
    This class determines how the results are generated. The strategy is displayed
    based on the definitions in StrategySectionDisplay.py
    """

    intention: Optional[str] = Field(
        "default", description="The intention identification strategy"
    )
    intention_list: Optional[List[str]] = Field(
        [], description="The list of intentions to be identified."
    )
    intention_options: Optional[Dict[str, Any]] = Field(
        None,
        description="The options for selected intention identification strategy.",
    )
    intention_sp_id: Optional[str] = Field(
        None, description="The system prompt id for intention identification"
    )
    intention_up_id: Optional[str] = Field(
        None,
        description="The user prompt id for intention identification. The"
        "intention_list will be passed in the prompt.",
    )

    rewrite: Optional[str] = Field(None, description="The query rewrite strategy")
    rewrite_options: Optional[Dict[str, Any]] = Field(
        None,
        description="The options for rewrite, right now support "
        "model_name (using the same client as the inference).",
    )
    rewrite_sp_ids: Optional[Dict[str, str]] = Field(
        {},
        description="The system prompt ids for query rewrite. The key is the intent. "
        "If the intent is not in the dict, the default rewrite will be used.",
    )
    rewrite_up_ids: Optional[Dict[str, str]] = Field(
        {},
        description="The user prompt ids for query rewrite. The key is the intent. "
        "If the intent is not in the dict, the default rewrite will be used.",
    )

    search: Optional[str] = Field(
        None, description="The search strategy, possible values are simple and hybrid."
    )
    search_options: Optional[Dict[str, Any]] = Field(
        {SEARCH_OPTION_TOP_K: 20, SEARCH_OPTION_METRIC: "COSINE"},
        description="The metric to use for dense search",
    )

    rerank: Optional[str] = Field(None, description="The answer reranking strategy")
    rerank_options: Optional[Dict[str, Any]] = Field(
        None, description="The options for rerank, right now support model_name."
    )

    enable_neighboring_context: Optional[bool] = Field(
        None, description="Whether to enable neighboring context."
    )

    target_model_name: str = Field(
        None,
        description="The target model name for inference, default set in env",
    )

    system_prompt_ids: Optional[Dict[str, Any]] = Field(
        {},
        description="The system prompt ids for the final question submission."
        "The key is the intent. If the intent is not in the dict, the default rewrite "
        "will be used.",
    )
    user_prompt_ids: Optional[Dict[str, Any]] = Field(
        {},
        description="The user prompt ids for the final question submission."
        "The key is the intent. If the intent is not in the dict, the default rewrite "
        "will be used.",
    )


class StrategyConfCreate(StrategyConfBase):

    strategy_name: str = Field(
        ..., description="The strategy name, required to be unique for a user."
    )

    strategy_description: Optional[str] = Field(
        None, description="The strategy description"
    )

    user_uuid: Optional[str] = Field(
        None, description="The owner's user_uuid. If None, it is a system strategy."
    )


class StrategyConf(StrategyConfCreate):
    strategy_id: str = Field(..., description="The strategy id")
    strategy_hash: str = Field(..., description="The hash of the strategy")
    strategy_version: str = Field(
        ..., description="The version of the strategy using a timestamp"
    )
    strategy_status: str = Field(
        StrategyStatus.ACTIVE, description="The strategy status"
    )
    is_system: bool = Field(
        False, description="Whether the strategy is a system strategy or not"
    )
    created_at: Optional[datetime] = Field(None, description="The creation time")
    updated_at: Optional[datetime] = Field(None, description="The last update time")
