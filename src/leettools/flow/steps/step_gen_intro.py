from typing import ClassVar, List, Optional, Type

from leettools.common.utils import config_utils, template_eval
from leettools.core.consts import flow_option
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.flow.step import AbstractStep
from leettools.flow.utils import flow_utils, prompt_utils


class StepGenIntro(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "gen_intro"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return prompt_utils.get_supported_template_option_items()

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        content: str,
        query_metadata: Optional[ChatQueryMetadata] = None,
    ) -> ArticleSection:
        """
        Given the content, usually the summary of the related documents, generate
        an introduction section for a research report. The query_metadata is optional
        and can be used to provide additional information about the query.

        Args:
        - exec_info: The execution information.
        - content: The content.
        - query_metadata: The query metadata.

        Returns:
        - The introduction section.
        """
        return _step_gen_intro_section(
            exec_info=exec_info,
            content=content,
            query_metadata=query_metadata,
        )


def _step_gen_intro_section(
    exec_info: ExecInfo,
    content: str,
    query_metadata: Optional[ChatQueryMetadata] = None,
) -> ArticleSection:

    display_logger = exec_info.display_logger
    display_logger.info("[Status]Generating introduction.")

    query = exec_info.target_chat_query_item.query_content

    output_lang = flow_utils.get_output_lang(
        exec_info=exec_info, query_metadata=query_metadata
    )
    if output_lang == "Chinese":
        intro_title = "简介"
    else:
        intro_title = "Introduction"

    flow_options = exec_info.flow_options
    content_instruction = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_CONTENT_INSTRUCTION,
        default_value="",
        display_logger=display_logger,
    )
    section_model = content_instruction = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_WRITING_MODEL,
        default_value=exec_info.settings.DEFAULT_WRITING_MODEL,
        display_logger=display_logger,
    )

    api_caller = exec_info.get_inference_caller()
    if section_model is None:
        section_model = api_caller.model_name

    content = flow_utils.limit_content(content, section_model, display_logger)

    user_prompt_template = f"""
{{{{ context_presentation }}}}, please generate an introduction section for a research report
about { query }  {{{{ lang_instruction }}}}
{ content_instruction }

Return the result as a string, do not include the title in the result.
            
Here is the query:
{{{{ rewritten_query }}}}

Here is the content:
{{{{ context }}}}
"""

    system_prompt_template = """
You are an expert of analyzing the content of the document and write an introduction
section for the conttent.
"""

    user_prompt = template_eval.render_template(
        user_prompt_template,
        prompt_utils.get_template_vars(
            flow_options=flow_options,
            inference_context=content,
            rewritten_query=query,
            lang=output_lang,
        ),
    )

    response_str, _ = api_caller.run_inference_call(
        system_prompt=system_prompt_template,
        user_prompt=user_prompt,
        need_json=False,
        call_target="get_intro",
        override_model_name=section_model,
    )

    intro_section = ArticleSection(
        title=intro_title,
        content=response_str,
        plan=ArticleSectionPlan(
            title=intro_title,
            search_query=query,
            user_prompt_template=user_prompt_template,
            system_prompt_template=system_prompt_template,
        ),
    )

    return intro_section
