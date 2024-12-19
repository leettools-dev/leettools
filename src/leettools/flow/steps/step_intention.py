from typing import ClassVar, List, Type

from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.eds.rag.intention.intention_getter import (
    DEFAULT_INTENTION,
    get_intention_getter_by_strategy,
)
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep


class StepIntention(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "intention"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_step(exec_info: ExecInfo) -> ChatQueryMetadata:
        return _run_intention(exec_info=exec_info)


def _run_intention(
    exec_info: ExecInfo,
) -> ChatQueryMetadata:

    context = exec_info.context
    display_logger = exec_info.display_logger
    user = exec_info.user

    query = exec_info.target_chat_query_item.query_content
    intention_section = exec_info.strategy.strategy_sections.get(
        StrategySectionName.INTENTION, None
    )

    query_metadata = ChatQueryMetadata(intention=DEFAULT_INTENTION)
    if intention_section is None:
        display_logger.info(
            "Intention section is not provided. Using the default intention."
        )
        return query_metadata

    if (
        intention_section.strategy_name is None
        or intention_section.strategy_name == ""
        or intention_section.strategy_name == "disabled"
    ):
        display_logger.debug(
            "Intention strategy is disabled. Using the default intention."
        )
        return query_metadata

    display_logger.info("[Status]Getting intention for the query.")

    intention_getter = get_intention_getter_by_strategy(
        context=context,
        user=user,
        intention_section=intention_section,
        display_logger=display_logger,
    )
    query_metadata = intention_getter.get_intention(query)
    display_logger.info(f"The intention for original query is: {query_metadata}")
    return query_metadata
