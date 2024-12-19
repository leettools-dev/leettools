import traceback
from typing import ClassVar, List, Type

from leettools.common.logging import logger
from leettools.core.schemas.segment import SearchResultSegment
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.eds.rag.rerank.reranker import create_reranker_by_strategy
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep


class StepRerank(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "rerank"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        top_ranked_result_segments: List[SearchResultSegment],
    ) -> List[SearchResultSegment]:
        return _run_rerank(
            exec_info=exec_info,
            top_ranked_result_segments=top_ranked_result_segments,
        )


def _run_rerank(
    exec_info: ExecInfo,
    top_ranked_result_segments: List[SearchResultSegment],
) -> List[SearchResultSegment]:

    context = exec_info.context
    settings = exec_info.settings
    display_logger = exec_info.display_logger
    user = exec_info.user

    query: str = exec_info.target_chat_query_item.query_content
    rerank_section = exec_info.strategy.strategy_sections.get(
        StrategySectionName.RERANK, None
    )

    if rerank_section is None:
        display_logger.info("Rerank section is not provided. Skip reranking.")
        return top_ranked_result_segments

    if (
        rerank_section.strategy_name is None
        or rerank_section.strategy_name == ""
        or rerank_section.strategy_name == "disabled"
    ):
        display_logger.info(f"Rerank is disabled. Skip reranking.")
        return top_ranked_result_segments

    display_logger.info("[Status]Rerank the search results.")
    try:
        original_top_ranked_result_segments = top_ranked_result_segments.copy()
        reranker = create_reranker_by_strategy(
            context=context,
            user=user,
            rerank_section=rerank_section,
            display_logger=display_logger,
        )
        reranked_results = reranker.rerank(
            query=query,
            documents=top_ranked_result_segments,
            top_k=rerank_section.strategy_options.get(
                "top_k", settings.DEFAULT_SEARCH_TOP_K
            ),
            rerank_options=rerank_section.strategy_options,
        )

        top_ranked_result_segments = []
        for i in range(len(reranked_results.results)):
            result = reranked_results.results[i]
            top_rank_segment = SearchResultSegment.from_segment(
                result.segment, result.relevance_score
            )
            top_ranked_result_segments.append(top_rank_segment)
            logger().debug(f"Reranked segment #{i}: {top_rank_segment}")
    except Exception as e:
        # print out the trace of e
        trace = traceback.format_exc()
        logger().warning(f"Failed to run reranker: {e}. Using original results.")
        logger().debug(f"Detailed trace: {trace}")
        top_ranked_result_segments = original_top_ranked_result_segments
    return top_ranked_result_segments
