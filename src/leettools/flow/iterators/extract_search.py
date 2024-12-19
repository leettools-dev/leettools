from typing import Dict, List, Optional, Type

from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.iterator import AbstractIterator
from leettools.flow.utils.extract_helper import extract_from_document
from leettools.web.schemas.search_result import SearchResult


class ExtractSearch(AbstractIterator):

    from typing import ClassVar

    from leettools.flow.flow_component import FlowComponent
    from leettools.flow.flow_option_items import FlowOptionItem

    COMPONENT_NAME: ClassVar[str] = "ExtractSearch"

    @classmethod
    def short_description(cls) -> str:
        return "Extract structured information from search results."

    @classmethod
    def full_description(cls) -> str:
        return """
Extract information from all the documents in search results. We use
the search from find all documents that may contain the information.
We then extract the information from the whole document.
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
        search_results: List[SearchResult],
        extraction_instructions: str,
        target_model_name: str,
        model_class: Type[TypeVar_BaseModel],
        query_metadata: Optional[ChatQueryMetadata] = None,
        multiple_items: bool = True,
    ) -> Dict[str, List[TypeVar_BaseModel]]:
        """
        Extract information from all the documents in search results. We use
        the search from find all documents that may contain the information.
        We then extract the information from the whole document.

        Args:
        - exec_info: The execution information.
        - search_results: The search results.
        - extraction_instructions: The extraction instructions.
        - target_model_name: The target model name that will should be extracted.
        - model_class: The model class to use.
        - query_metadata: The query metadata.
        - multiple_items: Whether we should extract multiple items.

        Returns:
        - The extracted information as a dictionary where the key is the document
          original uri and the value is the list of extracted data.
        """

        context = exec_info.context
        document_store = context.get_repo_manager().get_document_store()
        org = exec_info.org
        kb = exec_info.kb
        display_logger = exec_info.display_logger

        display_logger.info(
            "[Status]Extracting information from documents from local search ..."
        )

        # the accummulated results, the key is the uri and the value is the list of extracted data
        return_objs: Dict[str, List[TypeVar_BaseModel]] = {}

        for search_result in search_results:
            if search_result.document_uuid is None:
                display_logger.warning(
                    f"Document UUID is None for local search result {search_result.href}. Ignored."
                )
                continue
            document = document_store.get_document_by_id(
                org, kb, search_result.document_uuid
            )
            if document is None:
                display_logger.warning(
                    f"Document {search_result.document_uuid} not found for local search result {search_result.href}. Ignored."
                )
                continue

            try:
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
            f"Finished extracting information from local search result."
        )
        return return_objs
