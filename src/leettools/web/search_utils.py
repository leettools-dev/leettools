from typing import Any, Dict, Tuple

from leettools.common.logging import EventLogger
from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.settings import SystemSettings


def get_common_search_paras(
    flow_options: Dict[str, Any], settings: SystemSettings, display_logger: EventLogger
) -> Tuple[int, int]:

    days_limit = config_utils.get_int_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_DAYS_LIMIT,
        default_value=0,
        display_logger=display_logger,
    )

    if days_limit < 0:
        display_logger.warning(
            f"Days limit is set to {days_limit}, which is negative."
            f"Setting it to default value 0."
        )
        days_limit = 0

    search_max_results = config_utils.get_int_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_SEARCH_MAX_RESULTS,
        default_value=10,
        display_logger=display_logger,
    )

    if search_max_results == 0:
        display_logger.warning(
            f"Max results is set to 0, which means no search will be performed."
            f"Setting it to default value 10."
        )
        search_max_results = 10
    if search_max_results > settings.SEARCH_MAX_RESULTS_FROM_RETRIEVER:
        display_logger.warning(
            f"Max results is set to {search_max_results}, which is too large."
            f"Setting it to {settings.SEARCH_MAX_RESULTS_FROM_RETRIEVER}."
        )
        search_max_results = settings.SEARCH_MAX_RESULTS_FROM_RETRIEVER

    return days_limit, search_max_results
