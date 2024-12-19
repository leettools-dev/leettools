from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName


class StrategySection(BaseModel):

    # the name of the section, should correspond to a step name
    section_name: StrategySectionName

    # used in the config file to specify the actual section
    # for example, for search step, we can have "simple" or "hybrid"
    # for rerank step, we can have "rerank" or "local"
    strategy_name: Optional[str] = None  # None means disabled

    strategy_options: Optional[Dict[str, Any]] = None  # Any other customized options

    # API model options
    api_provider_username: Optional[str] = None
    api_provider_config_name: Optional[str] = None
    api_model_name: Optional[str] = None
    api_model_options: Optional[Dict[str, Any]] = None

    # we provide prompts per intention
    intention_list: Optional[List[str]] = None

    # default prompts
    llm_system_prompt_id: Optional[str] = None
    llm_user_prompt_id: Optional[str] = None
    # prompts by intention
    llm_system_prompt_ids_by_intention: Optional[Dict[str, str]] = None
    llm_user_prompt_ids_by_intention: Optional[Dict[str, str]] = None
