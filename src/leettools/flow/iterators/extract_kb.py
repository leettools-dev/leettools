from datetime import datetime
from typing import Dict, List, Optional, Type

from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.docsource import DocSource
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.iterator import AbstractIterator
from leettools.flow.iterators.document_iterator import document_iterator
from leettools.flow.utils.extract_helper import extract_from_document


class ExtractKB(AbstractIterator):

    from typing import ClassVar

    from leettools.flow.flow_component import FlowComponent
    from leettools.flow.flow_option_items import FlowOptionItem

    COMPONENT_NAME: ClassVar[str] = "ExtractKB"

    @classmethod
    def short_description(cls) -> str:
        return "Extract structured information from documents in a KB."

    @classmethod
    def full_description(cls) -> str:
        return """
Given a pydantic model, extract structured information from the documents in a KB with
a filter or specified docsource.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [steps.StepExtractInfo]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractIterator.direct_flow_option_items() + []

    @staticmethod
    def run(
        exec_info: ExecInfo,
        extraction_instructions: str,
        target_model_name: str,
        model_class: Type[TypeVar_BaseModel],
        docsource: Optional[DocSource] = None,
        query_metadata: Optional[ChatQueryMetadata] = None,
        multiple_items: bool = True,
        updated_time_threshold: Optional[datetime] = None,
    ) -> Dict[str, List[TypeVar_BaseModel]]:
        """
        Extract information from the KB in the exec_info or the docsource if specified.
        If the information has been extracted before, the existing data will be returned
        as well.

        Args:
        - exec_info: The execution information.
        - extraction_instructions: The extraction instructions.
        - target_model_name: The target model name that will should be extracted.
        - model_class: The model class to use.
        = docsource: The docsource to extract from, if none, extract from the KB.
        - query_metadata: The query metadata.
        - multiple_items: Whether we should extract multiple items.
        - updated_time_threshold: The threshold for the updated time.

        Returns:
        - The extracted information as a dictionary where
            the key is the document original uri and the value is the list of extracted data.
        """
        kb = exec_info.kb
        display_logger = exec_info.display_logger

        display_logger.info(
            "[Status]Extracting information from documents in the knowledgebase ..."
        )

        # the accummulated results
        # the key is the uri and the value is the list of extracted data
        return_objs: Dict[str, List[TypeVar_BaseModel]] = {}

        def docsource_filter(_: ExecInfo, docsource: DocSource) -> bool:
            if (
                updated_time_threshold is not None
                and docsource.updated_at < updated_time_threshold
            ):
                display_logger.info(
                    f"Docsource {docsource.display_name} has updated_time "
                    f"{docsource.updated_at} before {updated_time_threshold}. Skipped."
                )
                return False
            return True

        for document in document_iterator(
            exec_info=exec_info, docsource=docsource, docsource_filter=docsource_filter
        ):
            try:
                doc_original_uri = document.original_uri
                if doc_original_uri is None:
                    doc_original_uri = document.doc_uri

                extract_from_document(
                    return_objs=return_objs,
                    exec_info=exec_info,
                    document=document,
                    extraction_instructions=extraction_instructions,
                    model_class=model_class,
                    model_class_name=target_model_name,
                    query_metadata=query_metadata,
                    multiple_items=multiple_items,
                )
            except Exception as e:
                display_logger.warning(
                    f"Failed to extract from document {document.document_uuid}: {e}. Ignored."
                )
                continue

        display_logger.info(
            f"Finished extracting information from knowledgebase {kb.name}."
        )
        return return_objs
