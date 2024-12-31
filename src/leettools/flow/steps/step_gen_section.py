from typing import ClassVar, Dict, List, Type

from leettools.common.utils import config_utils
from leettools.common.utils.template_eval import render_template
from leettools.core.consts import flow_option
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.strategy.schemas.prompt import PromptBase
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.flow.step import AbstractStep
from leettools.flow.utils import flow_utils, prompt_utils


class StepGenSection(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "gen_section"

    @classmethod
    def short_description(cls) -> str:
        return "Generate a section based on the plan."

    @classmethod
    def full_description(cls) -> str:
        return """Based on the article section plan, search the local KB for related
information and generate the section following the instructions in the plan and the 
options set in the query such as style, words, language, etc.
"""

    @classmethod
    def used_prompt_templates(cls) -> Dict[str, PromptBase]:
        # The templates are defined in the section plan.
        return {}

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return prompt_utils.get_supported_template_option_items() + [
            flow_option_items.FOI_PLANNING_MODEL(),
        ]

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        section_plan: ArticleSectionPlan,
        query_metadata: ChatQueryMetadata,
        extended_context: str,
        rewritten_query: str,
        previous_sections: list[ArticleSection],
    ) -> ArticleSection:
        """
        Generate a section based on the plan.

        Args:
        - exec_info: The execution information.
        - section_plan: The section plan.
        - query_metadata: The query metadata.
        - extended_context: The extended context.
        - rewritten_query: The rewritten query.
        - sections: The existing sections.

        Returns:
        - The generated section.
        """
        display_logger = exec_info.display_logger
        display_logger.info(f"[Status]Generating section {section_plan.title}.")

        api_caller = exec_info.get_inference_caller()

        output_lang = flow_utils.get_output_lang(
            exec_info=exec_info, query_metadata=query_metadata
        )

        flow_options = exec_info.flow_options
        if flow_options is None:
            flow_options = {}

        user_template_vars = prompt_utils.get_template_vars(
            flow_options=flow_options,
            inference_context=extended_context,
            rewritten_query=rewritten_query,
            lang=output_lang,
        )

        # Note: tried this approach, not working very well
        # concatenate previous sections
        # user_template_vars["previous_sections"] = "\n".join(
        #    [f"{section.title}\n{section.content}" for section in sections]
        # )

        # the template is generated in the subflow_gen_essay.py

        final_system_prompt = render_template(
            section_plan.system_prompt_template, user_template_vars
        )

        final_user_prompt = render_template(
            section_plan.user_prompt_template,
            user_template_vars,
        )

        section_model = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_WRITING_MODEL,
            default_value=exec_info.settings.DEFAULT_WRITING_MODEL,
            display_logger=display_logger,
        )
        display_logger.info(f"Using {section_model} to generate the section content.")

        response_str, _ = api_caller.run_inference_call(
            system_prompt=final_system_prompt,
            user_prompt=final_user_prompt,
            need_json=False,
            call_target="section generation",
            override_model_name=section_model,
        )

        display_logger.info("Query finished successfully.")

        return ArticleSection(
            title=section_plan.title, content=response_str, plan=section_plan
        )
