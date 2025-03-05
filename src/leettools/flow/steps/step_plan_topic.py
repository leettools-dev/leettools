from typing import ClassVar, Dict, List, Optional, Type

from leettools.common import exceptions
from leettools.common.utils import config_utils, template_eval
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
from leettools.flow.schemas.article import TopicList
from leettools.flow.step import AbstractStep
from leettools.flow.utils import flow_utils, prompt_utils


class StepPlanTopic(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "plan_topic"

    @classmethod
    def short_description(cls) -> str:
        return "Generate a topic plan from the content provided."

    @classmethod
    def full_description(cls) -> str:
        return """Read the content provided, usually a list of summaries of the related
documents, and generate a list of topics that are discussed in theese documents and 
the instructions to write detailed sections about these topics.
"""

    @classmethod
    def used_prompt_templates(cls) -> Dict[str, PromptBase]:
        topic_plan_template_str = """
{{ context_presentation }}, {{ num_of_section_instruction }} 
from the content as the outline for {{ article_style }} for this subject:

{{ query }}

{{ content_instruction }}

Please create the title for each topic {{ output_lang_instruction }}
For each topic, also generate a prompt {{ search_lang_instruction }}
that can guide the LLM to find the most relevant information and write a detailed section
about it. 

{{ json_format_instruction }}

{
    "topics": [
        { "title": "Topic 1", "prompt": "Prompt for topic 1" },
        { "title": "Topic 2", "prompt": "Prompt for topic 2" }
    ]
}

Here is the related content:
{{ content }}
"""
        return {
            cls.COMPONENT_NAME: PromptBase(
                prompt_category=PromptCategory.PLANNING,
                prompt_type=PromptType.USER,
                prompt_template=topic_plan_template_str,
                prompt_variables={
                    "context_presentation": "The context presentation.",
                    "num_of_section_instruction": "The instruction for the number of sections.",
                    "article_style": "The style of the article.",
                    "query": "The query.",
                    "content_instruction": "The instruction for the content.",
                    "output_lang_instruction": "The output language.",
                    "search_lang_instruction": "The search language.",
                    "json_format_instruction": "The instruction for the JSON format.",
                    "content": "The content.",
                },
            )
        }

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return [
            flow_option_items.FOI_NUM_OF_SECTIONS(),
            flow_option_items.FOI_ARTICLE_STYLE(),
            flow_option_items.FOI_PLANNING_MODEL(),
            flow_option_items.FOI_CONTENT_INSTRUCTION(),
        ]

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        content: str,
        query_metadata: Optional[ChatQueryMetadata] = None,
    ) -> TopicList:
        """
        Get a topic list from the content, usually a summary of the related contents,

        Args:
        - exec_info: The execution information.
        - content: The content.
        - query_metadata: The query metadata.

        Returns:
        - The list of topics.
        """
        query = exec_info.target_chat_query_item.query_content
        num_of_sections = config_utils.get_int_option_value(
            options=exec_info.flow_options,
            option_name=flow_option.FLOW_OPTION_NUM_OF_SECTIONS,
            default_value=None,
            display_logger=exec_info.display_logger,
        )

        return _step_plan_topic_for_style(
            exec_info=exec_info,
            query=query,
            content=content,
            num_of_sections=num_of_sections,
            query_metadata=query_metadata,
        )


def _step_plan_topic_for_style(
    exec_info: ExecInfo,
    query: str,
    content: str,
    num_of_sections: Optional[int] = None,
    query_metadata: Optional[ChatQueryMetadata] = None,
) -> TopicList:
    """
    Get a topic list from the content.

    Args:
    - exec_info: The execution information.
    - query: The query.
    - content: The content.
    - num_of_sections: The number of sections to generate.
    - query_metadata: The query metadata.

    Returns:
    - The list of topics.
    """
    display_logger = exec_info.display_logger
    display_logger.info("[Status]Planning topics for research article.")

    if num_of_sections is None or num_of_sections == 0:
        num_of_section_instruction = "generate a list of most relevant topics"
    else:
        if num_of_sections == 1:
            num_of_section_instruction = "generate a topic"
        else:
            num_of_section_instruction = (
                f"generate {num_of_sections} most relevant topics"
            )

    flow_options = exec_info.flow_options
    article_style = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_ARTICLE_STYLE,
        default_value=flow_option_items.FOI_ARTICLE_STYLE().default_value,
        display_logger=display_logger,
    )
    planning_model = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_PLANNING_MODEL,
        default_value=flow_option_items.FOI_PLANNING_MODEL(
            exec_info.context
        ).default_value,
        display_logger=display_logger,
    )
    content_instruction = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_CONTENT_INSTRUCTION,
        default_value="Please only include the topics related to the above subject most.",
        display_logger=display_logger,
    )

    exec_info.display_logger.info(
        f"Using {planning_model} to generate the topic for research."
    )

    search_lang = flow_utils.get_search_lang(
        exec_info=exec_info, query_metadata=query_metadata
    )
    output_lang = flow_utils.get_output_lang(
        exec_info=exec_info, query_metadata=query_metadata
    )

    api_caller = exec_info.get_inference_caller()
    if planning_model is None:
        planning_model = api_caller.model_name

    content = flow_utils.limit_content(
        content=content, model_name=planning_model, display_logger=display_logger
    )

    system_prompt = (
        f"You are an expert of writing {article_style} for the specified query."
    )

    prompt_base = StepPlanTopic.used_prompt_templates()[StepPlanTopic.COMPONENT_NAME]
    user_prompt_template = prompt_base.prompt_template

    template_vars = {
        "context_presentation": prompt_utils.context_presentation(),
        "num_of_section_instruction": num_of_section_instruction,
        "article_style": article_style,
        "query": query,
        "content_instruction": content_instruction,
        "output_lang_instruction": prompt_utils.lang_instruction(output_lang),
        "search_lang_instruction": prompt_utils.lang_instruction(search_lang),
        "json_format_instruction": prompt_utils.json_format_instruction(),
        "content": content,
    }

    for var in prompt_base.prompt_variables.keys():
        if var not in template_vars:
            raise exceptions.MissingParametersException(missing_parameter=var)

    user_prompt = template_eval.render_template(user_prompt_template, template_vars)

    response_str, _ = api_caller.run_inference_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        need_json=True,
        call_target="get_topic_list",
        override_model_name=planning_model,
    )
    try:
        topic_list = TopicList.model_validate_json(response_str)
    except Exception as e:
        display_logger.error(f"ModelValidating TopicList failed: {response_str}")
        raise e
    return topic_list
