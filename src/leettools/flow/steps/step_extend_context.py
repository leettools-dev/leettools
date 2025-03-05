import re
from typing import ClassVar, Dict, List, Optional, Tuple, Type

from leettools.common.logging import logger
from leettools.common.models.model_info import ModelInfoManager
from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.core.schemas.chat_query_result import AnswerSource, SourceItem
from leettools.core.schemas.segment import SearchResultSegment
from leettools.core.strategy.schemas.strategy_section import StrategySectionName
from leettools.eds.api_caller.api_utils import get_default_inference_model_for_user
from leettools.eds.pipeline.split.splitter import remove_heading_from_content
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep


class StepExtendContext(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "extend_context"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        reranked_result: List[SearchResultSegment],
        accumulated_source_items: Dict[str, SourceItem],
        override_model_name: Optional[str] = None,
    ) -> Tuple[str, int, Dict[str, SourceItem]]:
        """
        Generate the extended context based on the reranked result.

        Args:
        - exec_info: The execution information.
        - reranked_result: The reranked search result.
        - accumulated_source_items: The accumulated source items.
        - override_model_name: The model name to override the default model name.

        Returns:
        The tuple of
        - the extended context
        - the context token count
        - the dictionary of accumualated source items, the key is the segment uuid.
        """

        context_section = exec_info.strategy.strategy_sections.get(
            StrategySectionName.CONTEXT, None
        )
        inference_section = exec_info.strategy.strategy_sections.get(
            StrategySectionName.INFERENCE, None
        )

        context = exec_info.context
        settings = exec_info.settings
        display_logger = exec_info.display_logger
        org = exec_info.org
        kb = exec_info.kb

        display_logger.debug(
            f"Incoming with accumulated_source_items so far: {len(accumulated_source_items)}."
        )

        from leettools.common.utils.tokenizer import Tokenizer

        if override_model_name is None:
            if (
                inference_section is not None
                and inference_section.api_model_name is not None
            ):
                inference_model_name = inference_section.api_model_name
                display_logger.debug(
                    f"Using model {inference_model_name} specified in the strategy for inference."
                )
            else:
                inference_model_name = get_default_inference_model_for_user(
                    context=context, user=exec_info.user
                )
                display_logger.debug(
                    f"Using the default model {inference_model_name} for inference."
                )
        else:
            inference_model_name = override_model_name
            display_logger.debug(f"Using the override model {inference_model_name}.")

        tokenizer = Tokenizer(settings)

        extended_context = ""

        flow_options = exec_info.flow_options
        context_limit = config_utils.get_int_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_CONTEXT_LIMIT,
            default_value=None,
            display_logger=display_logger,
        )
        if context_limit is None:
            context_limit = ModelInfoManager().get_context_size(
                inference_model_name, display_logger=display_logger
            )
            display_logger.info(
                f"Using the context limit from the model info: {context_limit}."
            )
        else:
            display_logger.info(
                f"Using the context limit from the flow options: {context_limit}."
            )

        display_logger.info(
            f"Creating references from vector search result for model {inference_model_name}, "
            f"Using {context_limit - 1000} toekns for the references."
        )
        context_limit = context_limit - 1000

        context_token_count = 0
        current_source_items: Dict[str, SourceItem] = {}
        total_source_count = len(accumulated_source_items)
        display_logger.debug(
            f"Accumulated source items before extension: {total_source_count}."
        )

        enable_neighboring_context = False
        if context_section is not None:
            if (
                context_section.strategy_name == "default"
                or context_section.strategy_name == "true"
            ):
                if context_section.strategy_options is not None:
                    enable_neighboring_context = config_utils.get_bool_option_value(
                        options=context_section.strategy_options,
                        option_name="enable_neighboring_context",
                        default_value=False,
                        display_logger=display_logger,
                    )

        if enable_neighboring_context:
            from leettools.eds.rag.context.neighboring_extension import (
                NeighboringExtension,
            )

            neighboring_extension = NeighboringExtension(context=context)
            display_logger.info("Neighboring context expansion enabled.")

        for result_segment in reranked_result:
            source_item = None
            if result_segment.segment_uuid not in accumulated_source_items:
                total_source_count += 1
                index = total_source_count
            else:
                source_item = accumulated_source_items[result_segment.segment_uuid]
                answer_source = source_item.answer_source
                index = source_item.index

            # becaue answer_source saves only the content after remove_heading_from_content
            # so we need to compute the content again
            segment_content = result_segment.content
            if enable_neighboring_context:
                # segments_set is used to keep track of all the segments that have been
                # used in the context
                segments_set = set()
                for segement in reranked_result:
                    segments_set.add(segement.segment_uuid)
                segment_content = neighboring_extension.get_neighboring_context(
                    org=org,
                    kb=kb,
                    segment=result_segment,
                    segments_set=segments_set,
                )

            segment_token_count = tokenizer.token_count(segment_content)
            if (context_token_count + segment_token_count) > context_limit:
                display_logger.info(
                    f"Reference token count exceeds {context_limit}. "
                    f"Using only the first {total_source_count - 1} results."
                )
                break

            logger().debug(f"Using segment: {result_segment.segment_uuid}")
            compact_str = re.sub(r"\n\s*\n+", "\n", segment_content)
            extended_context = f"[{index}] {compact_str}\n" + extended_context
            context_token_count += segment_token_count

            if source_item is None:
                answer_source = AnswerSource(
                    source_document_uuid=result_segment.document_uuid,
                    source_uri=result_segment.doc_uri,
                    source_content=f"[{index}] {remove_heading_from_content(result_segment.content)}",
                    score=result_segment.search_score,
                    position_in_doc=result_segment.position_in_doc,
                    start_offset=result_segment.start_offset,
                    end_offset=result_segment.end_offset,
                    original_uri=result_segment.original_uri,
                )
                source_item = SourceItem(
                    index=index,
                    source_segment_id=result_segment.segment_uuid,
                    answer_source=answer_source,
                )
                accumulated_source_items[result_segment.segment_uuid] = source_item
            current_source_items[result_segment.segment_uuid] = source_item

        display_logger.info(
            f"Total accumulated source items: {len(current_source_items)}."
        )

        return (
            extended_context,
            context_token_count,
            current_source_items,
        )
