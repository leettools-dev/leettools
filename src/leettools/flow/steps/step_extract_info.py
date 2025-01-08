from typing import ClassVar, Dict, List, Optional, Type

from pydantic import create_model

from leettools.common import exceptions
from leettools.common.utils import config_utils, json_utils, template_eval
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.consts import flow_option
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.strategy.schemas.prompt import (
    PromptBase,
    PromptCategory,
    PromptType,
)
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep
from leettools.flow.utils import flow_utils, prompt_utils


class StepExtractInfo(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "extract_info"

    @classmethod
    def short_description(cls) -> str:
        return "Extract information from the document."

    @classmethod
    def full_description(cls) -> str:
        return """Extract information from the document. The function will always 
return a list of the model class. If the instruction says to only extract one object, 
the caller should take the first object from the list.
"""

    @classmethod
    def used_prompt_templates(cls) -> Dict[str, PromptBase]:
        # See [src/leettools/flow/README.md] for how to use template varaibles
        extract_info_template_str = """
Given the provided content, please follow the instructions and return the results
{{ lang_instruction }}: 
{{ extraction_instructions }}

Below is the provided content:
{{ content }}
"""
        return {
            cls.COMPONENT_NAME: PromptBase(
                prompt_category=PromptCategory.EXTRACTION,
                prompt_type=PromptType.USER,
                prompt_template=extract_info_template_str,
                prompt_variables={
                    "content": "The content to extract information from.",
                    "extraction_instructions": "The instructions to extract the information.",
                    "lang_instruction": "The language instruction.",
                },
            )
        }

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        content: str,
        extraction_instructions: str,
        model_class: Type[TypeVar_BaseModel],
        model_class_name: str,
        multiple_items: bool,
        query_metadata: Optional[ChatQueryMetadata] = None,
    ) -> List[TypeVar_BaseModel]:
        """
        Get the required information from the content.

        The function will always return a list of the model class. If the instruction
        says to only extract one object, the caller should take the first object from
        the list.

        Args:
        - exec_info: The execution information.
        - content: The content to extract information from.
        - extraction_instructions: The instructions to extract the information.
        - model_class: The model class to extract the information.
        - model_class_name: The name of the model class.
        - multiple_items: Whether to extract multiple items.
        - query_metadata: The query metadata.

        Returns:
        - The list of extracted objects.
        """
        display_logger = exec_info.display_logger
        display_logger.info(
            f"[Status]StepExtractInfo: extract {model_class_name} from content."
        )
        flow_options = exec_info.flow_options

        summary_model = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_SUMMARIZING_MODEL,
            default_value=exec_info.settings.DEFAULT_SUMMARIZING_MODEL,
            display_logger=display_logger,
        )

        api_caller = exec_info.get_inference_caller()
        if summary_model is None:
            summary_model = api_caller.model_name

        content = flow_utils.limit_content(content, summary_model, display_logger)

        output_lang = flow_utils.get_output_lang(
            exec_info=exec_info, query_metadata=query_metadata
        )

        system_prompt = (
            "You are an expert of extract structured information from the document."
        )

        prompt_base = StepExtractInfo.used_prompt_templates()[
            StepExtractInfo.COMPONENT_NAME
        ]
        user_prompt_template = prompt_base.prompt_template

        template_vars = {
            "content": content,
            "extraction_instructions": extraction_instructions,
            "lang_instruction": prompt_utils.lang_instruction(output_lang),
        }

        for var in prompt_base.prompt_variables.keys():
            if var not in template_vars:
                raise exceptions.MissingParametersException(missing_parameter=var)

        user_prompt = template_eval.render_template(user_prompt_template, template_vars)

        if multiple_items:
            new_class_name = f"{model_class_name}_list"
            response_pydantic_model = create_model(
                new_class_name,
                items=(List[model_class], ...),
            )
        else:
            response_pydantic_model = model_class

        display_logger.debug(f"model_class: {model_class}")
        display_logger.debug(f"response_pydantic_model: {response_pydantic_model}")
        display_logger.debug(f"schema: {response_pydantic_model.model_json_schema()}")

        response_str, completion = api_caller.run_inference_call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            need_json=True,
            call_target="extract_info",
            override_model_name=summary_model,
            response_pydantic_model=response_pydantic_model,
        )

        display_logger.debug(f"response_str: {response_str}")

        # extract_result = json.loads(response_str)
        message = completion.choices[0].message
        if hasattr(message, "refusal"):
            if message.refusal:
                raise exceptions.LLMInferenceResultException(
                    f"Refused to extract information from the document: {message.refusal}."
                )

        if hasattr(message, "parsed"):
            display_logger.debug(f"Returning list of objects using message.parsed.")
            extract_result = message.parsed
            if multiple_items:
                return extract_result.items
            else:
                return [extract_result]
        else:
            display_logger.debug(
                f"Returning list of objects using model_validate_json."
            )
            response_str = json_utils.ensure_json_item_list(response_str)
            items = response_pydantic_model.model_validate_json(response_str)
            if multiple_items:
                return items.items
            else:
                return [items]
