from typing import ClassVar, List, Type

from openai.resources.chat.completions import ChatCompletion

from leettools.common.exceptions import UnexpectedCaseException
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.strategy.schemas.strategy_section import StrategySection
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName
from leettools.eds.rag.inference.inference import get_inference_by_strategy
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep
from leettools.flow.utils import flow_utils, prompt_utils


class StepInference(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "inference"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return prompt_utils.get_supported_template_option_items()

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        query_metadata: ChatQueryMetadata,
        rewritten_query: str,
        extended_context: str,
    ) -> ChatCompletion:
        """
        Run the inference API call to run the query.

        Args:
        - exec_info: The execution information.
        - query_metadata: The query metadata.
        - rewritten_query: The rewritten query.
        - extended_context: The extended context.

        Returns:
        - The chat completion.
        """
        context = exec_info.context
        display_logger = exec_info.display_logger
        user = exec_info.user
        org = exec_info.org
        kb = exec_info.kb

        query = exec_info.target_chat_query_item.query_content
        inference_section: StrategySection = exec_info.strategy.strategy_sections.get(
            StrategySectionName.INFERENCE, None
        )

        if inference_section is None:
            raise UnexpectedCaseException("Inference section is None.")

        display_logger.info(f"[Status]Running inference for query {query}.")

        inference = get_inference_by_strategy(
            context, user, inference_section, display_logger
        )

        output_lang = flow_utils.get_output_lang(
            exec_info=exec_info, query_metadata=query_metadata
        )

        template_vars = prompt_utils.get_template_vars(
            flow_options=exec_info.flow_options,
            inference_context=extended_context,
            rewritten_query=rewritten_query,
            lang=output_lang,
        )

        response_str, completion = inference.inference(
            org=org,
            kb=kb,
            query=query,
            query_metadata=query_metadata,
            template_vars=template_vars,
        )
        return completion
