import traceback
from typing import Dict, List, Optional, Tuple, Type

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.eds.extract.extract_store import (
    EXTRACT_DB_SOURCE_FIELD,
    EXTRACT_DB_TIMESTAMP_FIELD,
    create_extract_store,
)
from leettools.eds.rag.search.filter import BaseCondition
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.iterator import AbstractIterator
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
We then extract the information from the whole document. If specified
to use a backend store, existing data will be checked and returned 
if exists and the newly extracted data will be saved to the backend storage.
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
        save_to_backend: Optional[bool] = True,
    ) -> Tuple[Dict[str, List[TypeVar_BaseModel]], Dict[str, List[TypeVar_BaseModel]]]:
        """
        Extract information from all the documents in search results. We use
        the search from find all documents that may contain the information.
        We then extract the information from the whole document. If specified
        to use a backend store, existing data will be checked and returned
        if exists and the newly extracted data will be saved to the backend storage.

        Args:
        - exec_info: The execution information.
        - search_results: The search results.
        - extraction_instructions: The extraction instructions.
        - target_model_name: The target model name that will should be extracted.
        - model_class: The model class to use.
        - query_metadata: The query metadata.
        - multiple_items: Whether we should extract multiple items.
        - save_to_backend: Whether to save the extracted data to the backend.

        Returns:
        - The extracted information as two dictionaries:
            the key is the document original uri and the value is the list of extracted data.
            The first dictionary is the new extracted data.
            The second dictionary is the existing extracted data
        """

        context = exec_info.context
        document_store = context.get_repo_manager().get_document_store()
        org = exec_info.org
        kb = exec_info.kb
        display_logger = exec_info.display_logger

        display_logger.info(
            "[Status]Extracting information from documents from local search ..."
        )

        if save_to_backend:
            extract_store = create_extract_store(
                context=context,
                org=org,
                kb=kb,
                target_model_name=target_model_name,
                target_model_class=model_class,
            )

        # the accummulated results, the key is the uri and the value is the list of extracted data
        new_objs: Dict[str, List[TypeVar_BaseModel]] = {}
        existing_objs: Dict[str, List[TypeVar_BaseModel]] = {}

        for search_result in search_results:
            doc_original_uri = search_result.href
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

            if save_to_backend:
                filter = BaseCondition(
                    field=EXTRACT_DB_SOURCE_FIELD, operator="==", value=doc_original_uri
                )
                existing_objs_for_doc = extract_store.get_records(filter)
                if existing_objs_for_doc:
                    display_logger.debug(
                        f"Original URI {doc_original_uri} already extracted. Reading existing results."
                    )
                    existing_objs[doc_original_uri] = existing_objs_for_doc
                    continue

            try:
                display_logger.info(
                    f"[Status]ExtractSearch from document {document.original_uri} ..."
                )
                extracted_obj_list = steps.StepExtractInfo.run_step(
                    exec_info=exec_info,
                    content=document.content,
                    extraction_instructions=extraction_instructions,
                    model_class=model_class,
                    model_class_name=target_model_name,
                    multiple_items=multiple_items,
                    query_metadata=query_metadata,
                )

                if save_to_backend:
                    extended_obj_list = extract_store.save_records(
                        records=extracted_obj_list,
                        metadata={EXTRACT_DB_SOURCE_FIELD: doc_original_uri},
                    )
                else:
                    extended_obj_list = []
                    created_timestamp_in_ms = time_utils.cur_timestamp_in_ms()
                    for record in extracted_obj_list:
                        obj_dict = record.model_dump()
                        obj_dict[EXTRACT_DB_SOURCE_FIELD] = doc_original_uri
                        obj_dict[EXTRACT_DB_TIMESTAMP_FIELD] = created_timestamp_in_ms
                        extended_obj = model_class.model_validate(obj_dict)
                        extended_obj_list.append(extended_obj)

                # update the collection of extracted results
                display_logger.debug(extended_obj_list)
                if doc_original_uri in new_objs:
                    new_objs[doc_original_uri].append(extended_obj_list)
                else:
                    new_objs[doc_original_uri] = extended_obj_list

            except Exception as e:
                display_logger.warning(
                    f"Failed to extract from document {document.document_uuid}: {e}. Ignored."
                )
                display_logger.warning(traceback.format_exc())
                continue

        display_logger.info(
            f"Finished extracting information from local search result."
        )
        return new_objs, existing_objs
