import traceback
from typing import Callable, Dict, List, Optional, Tuple, Type

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.eds.extract.extract_store import (
    EXTRACT_DB_SOURCE_FIELD,
    EXTRACT_DB_TIMESTAMP_FIELD,
    create_extract_store,
)
from leettools.eds.rag.search.filter import BaseCondition
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.iterator import AbstractIterator
from leettools.flow.iterators.document_iterator import document_iterator


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
Given a pydantic model, extract structured information from the documents. If specified
to use a backend store, existing data will be checked and returned if exists and the 
newly extracted data will be saved to the backend storage.
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
        docsource_filter: Optional[Callable[[ExecInfo, DocSource], bool]] = None,
        docsink_filter: Optional[Callable[[ExecInfo, DocSink], bool]] = None,
        document_filter: Optional[Callable[[ExecInfo, Document], bool]] = None,
        query_metadata: Optional[ChatQueryMetadata] = None,
        multiple_items: Optional[bool] = True,
        save_to_backend: Optional[bool] = True,
    ) -> Tuple[Dict[str, List[TypeVar_BaseModel]], Dict[str, List[TypeVar_BaseModel]]]:
        """
        Extract information from the KB in the exec_info or the docsource if specified.
        If the information has been extracted before, the existing data will be returned
        as well.

        It is possible to just use the docsource_filter to filter out the target docsource.
        We allow to specify the docsource directly to avoid the need to get all docsources
        from the KB and then filter them.

        Args:
        - exec_info: The execution information.
        - extraction_instructions: The extraction instructions.
        - target_model_name: The target model name that will should be extracted.
        - model_class: The model class to use.
        - docsource: The docsource to extract from, if none, using the filter on all docsources in the KB.
        - docsource_filter: The docsource filter, ignored if docsource is specified.
        - docsink_filter: The docsink filter.
        - document_filter: The document filter.
        - query_metadata: The query metadata, usually created by the intention extraction.
        - multiple_items: Whether we should extract multiple items.
        - save_to_backend: Whether to save the extracted data to the backend.

        Returns:
        - The extracted information as two dictionaries:
            the key is the document original uri and the value is the list of extracted data.
            The first dictionary is the new extracted data.
            The second dictionary is the existing extracted data
        """
        context = exec_info.context
        org = exec_info.org
        kb = exec_info.kb
        display_logger = exec_info.display_logger

        display_logger.info(
            "[Status]Extracting information from documents in the knowledgebase ..."
        )

        if save_to_backend:
            extract_store = create_extract_store(
                context=context,
                org=org,
                kb=kb,
                target_model_name=target_model_name,
                target_model_class=model_class,
            )

        # the accummulated results
        # the key is the uri and the value is the list of extracted data
        new_objs: Dict[str, List[TypeVar_BaseModel]] = {}
        existing_objs: Dict[str, List[TypeVar_BaseModel]] = {}

        for document in document_iterator(
            exec_info=exec_info,
            docsource=docsource,
            docsource_filter=docsource_filter,
            docsink_filter=docsink_filter,
            document_filter=document_filter,
        ):
            try:
                doc_original_uri = document.original_uri
                if doc_original_uri is None:
                    doc_original_uri = document.doc_uri

                if save_to_backend:
                    filter = BaseCondition(
                        field=EXTRACT_DB_SOURCE_FIELD,
                        operator="==",
                        value=doc_original_uri,
                    )
                    existing_objs_for_doc = extract_store.get_records(filter)
                    if existing_objs_for_doc:
                        display_logger.debug(
                            f"Original URI {doc_original_uri} already extracted. Reading existing results."
                        )
                        existing_objs[doc_original_uri] = existing_objs_for_doc
                        continue
                    else:
                        display_logger.debug(
                            f"Extracting from document {document.document_uuid} ..."
                        )

                display_logger.info(
                    f"[Status]ExtractKB from document {document.original_uri} ..."
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
                    # manually add the fields needed
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
            f"Finished extracting information from knowledgebase {kb.name}."
        )
        return new_objs, existing_objs
