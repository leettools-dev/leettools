from typing import ClassVar, List, Optional, Type

from leettools.common.logging import logger
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep
from leettools.flow.utils import flow_utils, prompt_utils


class StepGenSearchPhrases(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "gen_search_phrases"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        query_metadata: Optional[ChatQueryMetadata] = None,
    ) -> str:
        """
        Generate search phrases for the query in the ExecInfo.

        Args:
        - exec_info: The execution information.
        - query_metadata (optional): The query metadata.

        Returns:
        - The generated search phrases
        """
        query = exec_info.target_chat_query_item.query_content
        return _step_get_search_phrases_for_query(
            exec_info=exec_info, query=query, query_metadata=query_metadata
        )


def _step_get_search_phrases_for_query(
    exec_info: ExecInfo,
    query: str,
    query_metadata: Optional[ChatQueryMetadata] = None,
) -> str:

    display_logger = exec_info.display_logger
    display_logger.info("[Status]Generating web search phrases.")

    search_lang = flow_utils.get_search_lang(
        exec_info=exec_info, query_metadata=query_metadata
    )
    logger().info(f"search_lang: {search_lang}")

    api_caller = exec_info.get_inference_caller()
    response_str, _ = api_caller.run_inference_call(
        system_prompt="You are an expert of creating good search phrases for a query topic.",
        user_prompt=f"""
Given the following query, create a web search query
{prompt_utils.lang_instruction(search_lang)}
that will return most relavant information about the query from the the web search engine.

Return the result as a string without quotes, do not include the title in the result.
            
Here is the query:
{query}
        """,
        need_json=False,
        call_target="get_search_query",
    )
    response_str = response_str.strip().strip('"')
    display_logger.info(
        f"Generated web search phrases: {response_str} for query {query}"
    )
    return response_str
