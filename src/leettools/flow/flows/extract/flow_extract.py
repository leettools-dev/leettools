import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Type

from pydantic import ConfigDict

from leettools.common import exceptions
from leettools.common.logging import EventLogger
from leettools.common.utils import config_utils
from leettools.common.utils.dynamic_exec_util import execute_pydantic_snippet
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.common.utils.template_eval import render_template
from leettools.core.consts import flow_option
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.prompt import (
    PromptBase,
    PromptCategory,
    PromptType,
)
from leettools.flow import flow_option_items, iterators, steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.utils import flow_utils
from leettools.web import search_utils
from leettools.web.retrievers.retriever import create_retriever

script_path = os.path.dirname(os.path.realpath(__file__))


class FlowExtract(AbstractFlow):
    """
    This flow will iterate the documents in the KB and extract information as
    instructed. The result will be displayed as a table in the output.
    """

    FLOW_TYPE: ClassVar[str] = "extract"
    ARTICLE_TYPE: ClassVar[str] = ArticleType.CSV.value
    COMPONENT_NAME: ClassVar[str] = "extract"

    @classmethod
    def short_description(cls) -> str:
        return "Extract information from the search results and output as csv."

    @classmethod
    def full_description(cls) -> str:
        return """
Extra structured data from web or local KB search results:
- Perform the search with retriever: "local" for local KB, a search engine (e.g., Google)
  fetches top documents from the web. If no KB is specified, create an adhoc KB; 
  otherwise, save and process results in the KB.
- New web search results are processed through the document pipeline: conversion, 
  chunking, and indexing.
- Extract structured data from matched documents based on the specified model.
- Display the extracted data as a table in the output.
"""

    @classmethod
    def used_prompt_templates(cls):
        instruction_py_template = """
from typing import List, Dict

from pydantic import BaseModel

instructions = \"\"\"
If the article contains the information about {{ query }}, extract the following information:

{{ schema }}

Use -1 for unknown numeric values and "n/a" for unknown string values.
\"\"\"

{{ schema }}
"""
        return {
            cls.COMPONENT_NAME: PromptBase(
                prompt_category=PromptCategory.EXTRACTION,
                prompt_type=PromptType.USER,
                prompt_template=instruction_py_template,
                prompt_variables={
                    "schema": "The Pydantic schema for the model class to extract.",
                    "query": "The query content.",
                },
            )
        }

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [steps.StepSearchToDocsource]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:

        return AbstractFlow.get_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True),
            flow_option_items.FOI_EXTRACT_PYDANTIC(explicit=True, required=True),
            flow_option_items.FOI_TARGET_SITE(),
            flow_option_items.FOI_SEARCH_LANGUAGE(),
            flow_option_items.FOI_SEARCH_MAX_RESULTS(),
            flow_option_items.FOI_DAYS_LIMIT(),
            flow_option_items.FOI_OUTPUT_LANGUAGE(),
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: Optional[EventLogger] = None,
    ) -> ChatQueryResultCreate:

        # common setup
        exec_info = ExecInfo(
            context=self.context,
            org=org,
            kb=kb,
            user=user,
            target_chat_query_item=chat_query_item,
            display_logger=display_logger,
        )

        display_logger = exec_info.display_logger
        flow_options = exec_info.flow_options

        fn = flow_option.FLOW_OPTION_EXTRACT_PYDANTIC
        pydantic_schema = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_EXTRACT_PYDANTIC,
            default_value=None,
            display_logger=display_logger,
        )
        if pydantic_schema is None:
            raise exceptions.ParametersValidationException(
                f"Missing required flow option {fn}."
            )

        # check if pydantic schema has multiple lines
        if "\n" not in pydantic_schema:
            filepath = Path(pydantic_schema)
            if filepath.is_absolute():
                if filepath.exists():
                    pydantic_schema = filepath.read_text()
                else:
                    raise exceptions.ParametersValidationException(
                        f"File {pydantic_schema} not found."
                    )
            else:
                code_root = exec_info.context.settings.CODE_ROOT_PATH
                filepath = Path.joinpath(code_root, "..", pydantic_schema).resolve()
                if filepath.exists():
                    pydantic_schema = filepath.read_text()
                else:
                    raise exceptions.ParametersValidationException(
                        f"File {pydantic_schema} not found at [{filepath}]"
                    )

        default_instruction_py_template = self.used_prompt_templates()[
            self.COMPONENT_NAME
        ].prompt_template

        schema_code = render_template(
            template_str=default_instruction_py_template,
            variables={
                "schema": pydantic_schema,
                "query": chat_query_item.query_content,
            },
        )
        var_dict, type_dict = execute_pydantic_snippet(schema_code)

        if len(type_dict) == 0:
            raise exceptions.ParametersValidationException(
                f"Failed to extract any model class from the schema spec\n{schema_code}."
            )

        err_msgs = []
        if "target_model_name" not in var_dict:
            if len(type_dict) > 1:
                err_msgs.append(
                    f"Specified more than one model but target_model not specfied."
                )
                target_model_name = None
            else:
                target_model_name = list(type_dict.keys())[0]
        else:
            target_model_name = var_dict["target_model_name"]

        if target_model_name is not None:
            if target_model_name not in type_dict:
                err_msgs.append(
                    f"Model class {target_model_name} not found in model_classes"
                )

        instructions = var_dict.get("instructions", None)
        if instructions is None or len(instructions) == 0:
            err_msgs.append("No extraction instructions found in the Python code.")

        key_fields = var_dict.get("key_fields", [])

        if len(key_fields) == 0:
            display_logger.info("No key fields specified in the Python code.")

        if len(err_msgs) > 0:
            raise exceptions.ParametersValidationException(err_msgs)

        # Need the following code to set the model_config for each model class
        # Otherwise OpenAI API call will fail with error message:
        # code: 400 - {'error': {'message': "Invalid schema for response_format 'xxx':
        # In context=(), 'additionalProperties' is required to be supplied and to be false",
        # 'type': 'invalid_request_error', 'param': 'response_format', 'code': None}}
        for model_name, model_class in type_dict.items():
            model_config = ConfigDict(extra="forbid")
            model_class.model_config = model_config

        target_model = type_dict[target_model_name]

        days_limit, max_results = search_utils.get_common_search_paras(
            flow_options=flow_options,
            settings=self.context.settings,
            display_logger=display_logger,
        )

        # the agent flow starts here
        retriever_type = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_RETRIEVER_TYPE,
            default_value=RetrieverType.GOOGLE,
            display_logger=display_logger,
        )

        extracted_objs_dict: Dict[str, List[TypeVar_BaseModel]] = {}

        if retriever_type == RetrieverType.LOCAL:
            retriever = create_retriever(
                retriever_type=retriever_type,
                context=self.context,
                org=org,
                kb=kb,
                user=user,
            )

            if max_results == -1:
                # run the full KB scan
                display_logger.info(
                    f"Specified to extract from all documents in the KB {kb.name}."
                )

                if days_limit != 0:
                    updated_time_threshold = datetime.now() - timedelta(days=days_limit)
                    display_logger.info(
                        f"Setting the updated_time_threshold to {updated_time_threshold}."
                    )
                else:
                    updated_time_threshold = None

                extracted_objs_dict = iterators.ExtractKB.run(
                    exec_info=exec_info,
                    docsource=None,
                    extraction_instructions=instructions,
                    target_model_name=target_model_name,
                    model_class=target_model,
                    query_metadata=None,
                    updated_time_threshold=updated_time_threshold,
                )

            else:
                search_results = retriever.retrieve_search_result(
                    query=chat_query_item.query_content,
                    flow_options=flow_options,
                    display_logger=display_logger,
                )

                extracted_objs_dict = iterators.ExtractSearch.run(
                    exec_info=exec_info,
                    search_results=search_results,
                    extraction_instructions=instructions,
                    target_model_name=target_model_name,
                    model_class=target_model,
                )

        else:
            docsource = steps.StepSearchToDocsource.run_step(exec_info=exec_info)

            # the key is the document.original_uri and the value is the list of extracted objects
            extracted_objs_dict = iterators.ExtractKB.run(
                exec_info=exec_info,
                docsource=docsource,
                extraction_instructions=instructions,
                target_model_name=target_model_name,
                model_class=target_model,
            )

        # convert the extracted objects to a csv table
        display_headers: List[str] = list(target_model.model_fields.keys())
        display_headers.append("doc_original_uri")
        rows_data: List[List] = []
        for doc_original_uri, extracted_objs in extracted_objs_dict.items():
            for obj in extracted_objs:
                row_data: List[str] = list(obj.model_dump().values())
                row_data.append(doc_original_uri)
                rows_data.append(row_data)

        return flow_utils.create_chat_result_with_csv_data(
            header=display_headers,
            rows=rows_data,
            exec_info=exec_info,
            query_metadata=None,
        )
