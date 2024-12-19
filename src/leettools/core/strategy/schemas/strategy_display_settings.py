from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.core.strategy.schemas.strategy_conf import (
    SEARCH_OPTION_METRIC,
    SEARCH_OPTION_TOP_K,
)
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName

"""
The following classes are used for the cli and front-end to display the options for each section.
"""


class StrategyOptionItemDisplay(BaseModel):
    name: str = Field(..., description="The name of the variable.")
    display_name: Optional[str] = Field(
        None, description="The display name of the variable."
    )
    description: Optional[str] = Field(
        None, description="The description of the variable."
    )
    value_type: Optional[str] = Field(
        "str",
        description="The type of the value," "currently support str, int, float, bool.",
    )
    default_value: Optional[str] = Field(
        None, description="The default value of the variable."
    )


class StrategySectionDisplay(BaseModel):
    section_name: str
    section_display_name: str
    section_description: Optional[str]
    default_strategy_name: str
    # the key is the strategy name, the value is the options for the strategy
    strategy_name_choices: Optional[Dict[str, List[StrategyOptionItemDisplay]]]
    use_api: Optional[bool] = True  # show the API selector
    use_api_with_model: Optional[bool] = True  # show the model selector
    use_llm_model: Optional[bool] = True  # show LLM model options and prompt editor
    use_prompts_by_intention: Optional[bool] = True  # show prompts by intention editor
    allow_disable: Optional[bool] = True  # show the disable radio button


"""
Options we allow user to specify on the UI.

Example: https://platform.openai.com/docs/api-reference/chat/create
"""
_llm_inference_options: Dict[str, StrategyOptionItemDisplay] = {
    "temperature": StrategyOptionItemDisplay(
        name="temperature",
        display_name="Temperature",
        description="The temperature for generation.",
        value_type="float",
        default_value="0.0",
    ),
    "max_tokens": StrategyOptionItemDisplay(
        name="max_tokens",
        display_name="Max Tokens",
        description="The maximum number of tokens to generate.",
        value_type="int",
        default_value="8192",
    ),
}

intention_section_display = StrategySectionDisplay(
    section_name=StrategySectionName.INTENTION,
    section_display_name="Intention Identification",
    section_description="The options for intention identification. ",
    default_strategy_name="default",
    strategy_name_choices={
        "default": [],  # no extra options for default other than the model options
    },
    user_api=True,
    use_api_with_model=True,
    use_llm_model=True,
    use_prompts_by_intention=False,
    allow_disable=True,
)

rewrite_section_display = StrategySectionDisplay(
    section_name=StrategySectionName.REWRITE,
    section_display_name="Query Rewrite",
    section_description="The options for query rewrite. ",
    default_strategy_name="default",
    strategy_name_choices={
        "default": [],  # no extra options for default other than the model options
    },
    user_api=True,
    use_api_with_model=True,
    use_llm_model=True,
    use_prompts_by_intention=True,
    allow_disable=True,
)

top_k_option_item_display = StrategyOptionItemDisplay(
    name=SEARCH_OPTION_TOP_K,
    display_name="Top K",
    description="The number of results to return",
    value_type="int",
    default_value="20",
)

dense_search_option_item_display = StrategyOptionItemDisplay(
    name=SEARCH_OPTION_METRIC,
    display_name="Dense Search Metric",
    description="The metric to use for dense search",
    value_type="str",
    default_value="COSINE",
)

search_section_display = StrategySectionDisplay(
    section_name=StrategySectionName.SEARCH,
    section_display_name="Search",
    section_description="The options for search. ",
    default_strategy_name="hybrid",
    strategy_name_choices={
        "hybrid": [top_k_option_item_display, dense_search_option_item_display],
        "simple": [top_k_option_item_display, dense_search_option_item_display],
    },
    use_api=False,
    use_api_with_model=False,
    use_llm_model=False,
    use_prompts_by_intention=False,
    allow_disable=False,
)

rerank_section_display = StrategySectionDisplay(
    section_name=StrategySectionName.RERANK,
    section_display_name="Rerank",
    section_description="The options for rerank. ",
    default_strategy_name="default",
    strategy_name_choices={
        "default": [],  # no extra options for default other than the model options
    },
    use_api=True,
    use_api_with_model=True,
    use_llm_model=False,
    use_prompts_by_intention=False,
    allow_disable=True,
)

context_section_display = StrategySectionDisplay(
    section_name=StrategySectionName.CONTEXT,
    section_display_name="Context Expansion",
    section_description="The options for context expansion. ",
    default_strategy_name="default",
    strategy_name_choices={
        "default": [
            StrategyOptionItemDisplay(
                name="enable_neighboring_context",
                display_name="Enable Neighboring Context",
                description="Whether to enable neighboring context.",
                value_type="bool",
                default_value="True",
            )
        ]
    },
    use_api=False,
    use_api_with_model=False,
    use_llm_model=False,
    use_prompts_by_intention=False,
    allow_disable=True,
)

inference_section_display = StrategySectionDisplay(
    section_name=StrategySectionName.INFERENCE,
    section_display_name="Inference",
    section_description="The options for inference. ",
    default_strategy_name="default",
    strategy_name_choices={
        "default": [],  # no extra options for default other than the model options
    },
    use_api=True,
    use_api_with_model=True,
    use_llm_model=True,
    use_prompts_by_intention=True,
    allow_disable=False,
)

general_section_display = StrategySectionDisplay(
    section_name=StrategySectionName.GENERAL,
    section_display_name="General",
    section_description="The general options. ",
    default_strategy_name="default",
    strategy_name_choices={
        "default": [
            StrategyOptionItemDisplay(
                name="keep_query_lanaugage",
                display_name="Keep Query Language",
                description="Use query language for rewrite / search / inference.",
                value_type="bool",
                default_value="True",
            )
        ],  # no extra options for default other than the model options
    },
    use_api=False,
    use_api_with_model=False,
    use_llm_model=False,
    use_prompts_by_intention=False,
    allow_disable=False,
)

_display_sections = [
    intention_section_display,
    rewrite_section_display,
    search_section_display,
    rerank_section_display,
    context_section_display,
    inference_section_display,
    general_section_display,
]


def get_strategy_display_sections() -> List[StrategySectionDisplay]:
    return _display_sections


def get_llm_inference_display_options() -> Dict[str, StrategyOptionItemDisplay]:
    return _llm_inference_options
