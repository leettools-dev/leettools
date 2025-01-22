from typing import ClassVar, Dict, List, Type

from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.core.schemas.chat_query_result import SourceItem
from leettools.core.strategy.schemas.strategy_display_settings import (
    StrategySectionName,
)
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.flow.subflow import AbstractSubflow


class SubflowGenSection(AbstractSubflow):
    """
    Subflow to generate a section based on the section plan.
    """

    COMPONENT_NAME: ClassVar[str] = "gen_section"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [
            steps.StepIntention,
            steps.StepVectorSearch,
            steps.StepExtendContext,
            steps.StepRerank,
            steps.StepGenSection,
        ]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_subflow(
        exec_info: ExecInfo,
        section_plan: ArticleSectionPlan,
        accumulated_source_items: Dict[str, SourceItem],
        previous_sections: List[ArticleSection],
    ) -> ArticleSection:
        """
        This function executes the task using the EDS system and generates a section
        based on the style. The accumulated_source_items is a dictionary that contains all the
        source items that have been collected so far. The function returns an ArticleSection
        and updates the accumulated_source_items with the new source items that are collected.

        Args:
        - exec_info: the execution information
        - section_plan: the section plan
        - accumulated_source_items: the accumulated source items
        - previous_sections: the sections that have been generated so far

        Returns:
        - the article section
        """

        # here we can just run the whole process
        # intention -> rewrite -> search -> rerank -> context expansion -> generate
        # however, since we know the intention, we can start from the search step.
        # also, how can we support loop / branches of the process?
        display_logger = exec_info.display_logger

        # search query is usually the original query + the section title
        search_query = section_plan.search_query
        query_metadata = steps.StepIntention.run_step(exec_info=exec_info)

        # we will not use the rewritten query for now
        # since most the section_plan already has an instruction for the query

        top_ranked_result_segments = steps.StepVectorSearch.run_step(
            exec_info=exec_info,
            query_metadata=query_metadata,
            rewritten_query=search_query,
        )

        if len(top_ranked_result_segments) == 0:
            return ArticleSection(
                title=section_plan.title,
                content="No related content found for this section.",
                plan=section_plan,
            )

        reranked_result = steps.StepRerank.run_step(
            exec_info=exec_info,
            top_ranked_result_segments=top_ranked_result_segments,
        )

        # we need the section model in context extension computation
        flow_options = exec_info.flow_options

        section_model = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_WRITING_MODEL,
            default_value=exec_info.settings.DEFAULT_WRITING_MODEL,
            display_logger=display_logger,
        )
        display_logger.info(f"Using {section_model} to compute the context.")

        extended_context, context_token_count, section_source_items = (
            steps.StepExtendContext.run_step(
                exec_info=exec_info,
                reranked_result=reranked_result,
                accumulated_source_items=accumulated_source_items,
                override_model_name=section_model,
            )
        )

        display_logger.info(
            f"The context text length is: {len(extended_context)}. "
            f"The token count is: {context_token_count}. "
            f"The number of new source items is: {len(section_source_items)}. "
            f"The number of existing source items is: {len(accumulated_source_items)}. "
        )

        article_section = steps.StepGenSection.run_step(
            exec_info=exec_info,
            section_plan=section_plan,
            query_metadata=query_metadata,
            extended_context=extended_context,
            rewritten_query=search_query,
            previous_sections=previous_sections,
        )
        return article_section
