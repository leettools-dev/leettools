from typing import ClassVar, Dict, List, Optional, Type

from leettools.common import exceptions
from leettools.common.utils import config_utils, template_eval
from leettools.core.consts import flow_option
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.schemas.document import Document
from leettools.core.schemas.document_metadata import DocumentSummary
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


class StepSummarize(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "summarize"

    @classmethod
    def short_description(cls) -> str:
        return "Summarizes the given document content using the specified model."

    @classmethod
    def full_description(cls) -> str:
        return """Given a document content as a string, summarize the content using 
the model specified as the summarization model in the flow option.
"""

    @classmethod
    def used_prompt_templates(cls) -> Dict[str, PromptBase]:
        # See [src/leettools/flow/README.md] for how to use template varaibles
        summarize_template_str = """
If the following content is relevant to the subject '{{ subject }}',
{{ content_instruction }}
please do the following tasks:
- write a concise summary of the document less than 100 words {{ lang_instruction }},
- get up to 10 keywords that the document is about {{ lang_instruction }}, 
- find up to 10 URL links in the document
- get the authors of the document if possible
- if there is an explicit publishing date in the document, get the content_date for document. 
- generate a relevance score between 1 and 100, 100 means 100% fit the content instruction above.
{{ json_format_instruction }}
{
    "summary": "The summary of the document",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "links": ["url1", "url2", "url3"]
    "authors": ["author1", "author2", "author3"]
    "content_date": "2000-01-01"
    "relevance_score": 11
}

If the content is not related to the subject '{{ subject }}' at all, return a relevance score
0.

Here is the content:
{{ content }}
"""
        return {
            "summarize": PromptBase(
                prompt_category=PromptCategory.SUMMARIZATION,
                prompt_type=PromptType.USER,
                prompt_template=summarize_template_str,
                prompt_variables={
                    "subject": None,
                    "content_instruction": None,
                    "lang_instruction": None,
                    "json_format_instruction": None,
                    "content": None,
                },
            )
        }

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return [
            flow_option_items.FOI_SUMMARY_MODEL(),
            flow_option_items.FOI_CONTENT_INSTRUCTION(),
        ]

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        document: Document,
        all_links: Dict[str, int],
        force_summarize: Optional[bool] = False,
    ) -> Optional[Document]:
        """
        Summarizes the given document content based on the queries and the model specified
        in the flow options.

        Args:
        - exec_info (ExecInfo): The execution information.
        - document (Document): The document to summarize.
        - all_links (Dict[str, int]): The dictionary of all links, this step will update
            the dictionary with the links found in the document.
        - force_summarize (bool): Whether to force summarize the document if the document
            has already been summarized.

        Returns:
        - Document: The updated document with the summarized information. If the document
            has not been processed yet, return None. If the document has already been
            summarized and force_summarize is False, return the document without updating.
        """

        display_logger = exec_info.display_logger
        org = exec_info.org
        kb = exec_info.kb
        context = exec_info.context
        document_store = context.get_repo_manager().get_document_store()

        display_logger.info(f"[Status]Summarizing document {document.original_uri}.")

        if document.embed_status != DocSourceStatus.COMPLETED:
            display_logger.info(
                f"Document {document.document_uuid} has not been processed yet."
            )
            return None

        if document.summary() is not None:
            if not force_summarize:
                display_logger.debug(
                    f"Document {document.document_uuid} has already been summarized."
                )
                return document

        document_summary = StepSummarize._summarize_content(
            exec_info=exec_info, content=document.content
        )
        document.auto_summary = document_summary

        # Only update the all_links if the document is relevant
        if document.summary().relevance_score >= context.settings.RELEVANCE_THRESHOLD:
            for link in document_summary.links:
                if link in all_links:
                    all_links[link] += 1
                else:
                    all_links[link] = 1

        display_logger.debug(f"The returned document summary is {document_summary}")
        updated_document = document_store.update_document(org, kb, document)
        return updated_document

    @staticmethod
    def _summarize_content(exec_info: ExecInfo, content: str) -> DocumentSummary:
        """
        Summarizes the given document content using the specified model.

        Args:
        - exec_info (ExecInfo): The execution information.
        - subject (str): The subject of the target search.
        - content (str): The document content to be summarized.

        Returns:
        - DocumentSummary: The summarized document information.

        """

        display_logger = exec_info.display_logger

        if exec_info.kb is None:
            raise exceptions.UnexpectedNullValueException(
                operation_desc="Summarize content", entity="Knowledgebase"
            )

        flow_options = exec_info.flow_options

        summary_model = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_SUMMARIZING_MODEL,
            default_value=exec_info.settings.DEFAULT_SUMMARIZING_MODEL,
            display_logger=display_logger,
        )

        # TODO: temporary solution, we probably want to use a more proper subject
        # presentation in the KB

        content_instruction = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_CONTENT_INSTRUCTION,
            default_value=None,
            display_logger=display_logger,
        )

        if content_instruction is None:
            kb_content_instruction = exec_info.kb.get_content_instruction()
            if kb_content_instruction is not None:
                content_instruction = f"based on the following content instruction:\n{kb_content_instruction}\n"
            else:
                content_instruction = ""

        subject = exec_info.query
        if subject is None or subject == "":
            subject = exec_info.kb.name

        api_caller = exec_info.get_inference_caller()
        if summary_model is None:
            summary_model = api_caller.model_name

        content = flow_utils.limit_content(content, summary_model, display_logger)

        prompt_base = StepSummarize.used_prompt_templates()["summarize"]
        summarize_prompt_template = prompt_base.prompt_template

        template_vars = prompt_utils.get_template_vars(
            flow_options=flow_options,
            inference_context=content,
            rewritten_query=exec_info.query,
            lang=exec_info.output_lang,
        )
        template_vars["subject"] = subject
        template_vars["content_instruction"] = content_instruction
        template_vars["content"] = content

        for var in prompt_base.prompt_variables.keys():
            if var not in template_vars:
                raise exceptions.MissingParametersException(missing_parameter=var)

        user_prompt = template_eval.render_template(
            summarize_prompt_template, template_vars
        )

        response_str, _ = api_caller.run_inference_call(
            system_prompt="You are an expert of analyzing the content of the document.",
            user_prompt=user_prompt,
            need_json=True,
            call_target="get_summary",
            override_model_name=summary_model,
            override_max_token=3000,
        )

        doc_summary = DocumentSummary.model_validate_json(response_str)

        # sometimes the LLM uses the provided example content as the result
        if "The summary of the document" in doc_summary.summary:
            doc_summary.summary = ""

        if doc_summary.keywords is not None:
            if len(doc_summary.keywords) > 0:
                if "keyword1" in doc_summary.keywords[0]:
                    doc_summary.keywords = []

        if doc_summary.links is not None:
            if len(doc_summary.links) > 0:
                if "url1" in doc_summary.links[0]:
                    doc_summary.links = []
                http_links = [x for x in doc_summary.links if x.startswith("http")]
                doc_summary.links = http_links

        if doc_summary.content_date is not None:
            if "2000-01-01" in doc_summary.content_date:
                doc_summary.content_date = None

        if doc_summary.authors is not None:
            if len(doc_summary.authors) > 0:
                if "author1" in doc_summary.authors[0]:
                    doc_summary.authors = []

        return doc_summary
