from typing import ClassVar, List, Optional, Type

from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.eds.rag.rewrite.rewrite import get_query_rewriter_by_strategy
from leettools.eds.rag.schemas.rewrite import Rewrite
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep


class StepQueryRewrite(AbstractStep):
    COMPONENT_NAME: ClassVar[str] = "query_rewrite"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractStep.get_flow_option_items()

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        query_metadata: ChatQueryMetadata,
        rewrite_section: Optional[StrategySection] = None,
    ) -> Rewrite:
        """
        Rewrite the query based on the strategy section and the query metadata.

        If rewrite_section is provided, use it directly.
        If rewrite_section is not provided, get it from the strategy.

        Args:
        - exec_info: the execution info
        - query_metadata: the query metadata
        - rewrite_section: the rewrite section

        Returns:
        - rewrite: the rewrite result
        """
        display_logger = exec_info.display_logger
        display_logger.info(
            f"[Status] Rewrite query: {exec_info.target_chat_query_item.query_content}"
        )
        if rewrite_section is None:
            rewrite_section = exec_info.strategy.strategy_sections.get(
                StrategySectionName.REWRITE, None
            )
        return _step_run_rewriter(
            exec_info=exec_info,
            rewrite_section=rewrite_section,
            query_metadata=query_metadata,
        )


def _step_run_rewriter(
    exec_info: ExecInfo,
    rewrite_section: StrategySection,
    query_metadata: ChatQueryMetadata,
) -> Rewrite:
    context = exec_info.context
    display_logger = exec_info.display_logger
    user = exec_info.user
    org = exec_info.org
    kb = exec_info.kb
    query_item = exec_info.target_chat_query_item

    rewritten_query = query_item.query_content
    if rewrite_section is None:
        display_logger.info("Intention section is not provided. Skip rewriting.")
        return Rewrite(rewritten_question=rewritten_query)
    if (
        rewrite_section.strategy_name is None
        or rewrite_section.strategy_name == ""
        or rewrite_section.strategy_name == "disabled"
    ):
        display_logger.info("Rewrite strategy is disabled. Skip rewriting.")
        return Rewrite(rewritten_question=rewritten_query)

    display_logger.info("[Status] Rewriting the query.")

    query_rewriter = get_query_rewriter_by_strategy(
        context=context,
        user=user,
        rewrite_section=rewrite_section,
        event_logger=display_logger,
    )
    rewrite = query_rewriter.rewrite(
        org=org,
        kb=kb,
        query_item=query_item,
        query_metadata=query_metadata,
    )
    display_logger.info(f"[Update] Rewritten result is: {rewrite}")
    return rewrite
