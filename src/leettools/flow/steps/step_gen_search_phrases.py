from typing import ClassVar, Dict, List, Optional, Type

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.utils import template_eval
from leettools.core.consts import flow_option
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.strategy.schemas.prompt import (
    PromptBase,
    PromptCategory,
    PromptType,
)
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep
from leettools.flow.utils import flow_utils, prompt_utils


class StepGenSearchPhrases(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "gen_search_phrases"

    @classmethod
    def short_description(cls) -> str:
        return "Generate search phrases for the query."

    @classmethod
    def full_description(cls) -> str:
        return f"""Generate search phrases for the query using {flow_option.FLOW_OPTION_SEARCH_LANGUAGE}
if set, otherwise using the original language.
"""

    @classmethod
    def used_prompt_templates(cls) -> Dict[str, PromptBase]:
        # See [src/leettools/flow/README.md] for how to use template varaibles
        search_phrase_template_str = """
Given the following query, create a web search query 
{{ lang_instruction }}
that will return most relavant information about the query from the the web search engine.

Return the result as a string without quotes, do not include the title in the result.
                
Here is the query:
{{ query }}
"""
        return {
            cls.COMPONENT_NAME: PromptBase(
                prompt_category=PromptCategory.REWRITE,
                prompt_type=PromptType.USER,
                prompt_template=search_phrase_template_str,
                prompt_variables={
                    "query": "The query to generate search phrases for.",
                    "lang_instruction": "The language instruction.",
                },
            )
        }

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return [flow_option_items.FOI_SEARCH_LANGUAGE()]

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

        display_logger = exec_info.display_logger
        display_logger.info("[Status]Generating web search phrases.")

        search_lang = flow_utils.get_search_lang(
            exec_info=exec_info, query_metadata=query_metadata
        )
        logger().info(f"search_lang: {search_lang}")

        api_caller = exec_info.get_inference_caller()

        prompt_base = StepGenSearchPhrases.used_prompt_templates()[
            StepGenSearchPhrases.COMPONENT_NAME
        ]
        user_prompt_template = prompt_base.prompt_template

        template_vars = {
            "query": query,
            "lang_instruction": prompt_utils.lang_instruction(search_lang),
        }
        for var in prompt_base.prompt_variables.keys():
            if var not in template_vars:
                raise exceptions.MissingParametersException(missing_parameter=var)

        user_prompt = template_eval.render_template(user_prompt_template, template_vars)
        display_logger.debug(user_prompt)

        response_str, _ = api_caller.run_inference_call(
            system_prompt="You are an expert of creating good search phrases for a query topic.",
            user_prompt=user_prompt,
            need_json=False,
            call_target="get_search_query",
        )
        response_str = response_str.strip().strip('"')
        display_logger.info(
            f"Generated web search phrases: {response_str} for query {query}"
        )
        return response_str
