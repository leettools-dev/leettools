from typing import Dict, List, Optional, Type

from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.document import Document
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo


def extract_from_document(
    return_objs: Dict[str, List[Type[TypeVar_BaseModel]]],
    exec_info: ExecInfo,
    document: Document,
    extraction_instructions: str,
    model_class: Type[TypeVar_BaseModel],
    model_class_name: str,
    query_metadata: Optional[ChatQueryMetadata] = None,
    multiple_items: bool = True,
) -> None:
    """
    Wrapper function to extract information from a document.

    Args:
    - return_objs: The dictionary to store the extracted objects, the key is the document uri.
    - exec_info: The execution information.
    - document: The document to extract information from.
    - extraction_instructions: The extraction instructions.
    - model_class: The model class to use.
    - model_class_name: The model class name.
    - query_metadata: The query metadata.
    - multiple_items: Whether we should extract multiple items.

    Returns:
    - None: the results are saved in the return_objs dictionary.

    """

    display_logger = exec_info.display_logger

    # this function is a simple wrapper of the actual operation
    # sometimes we have more complex operations to do
    extracted_obj_list = steps.StepExtractInfo.run_step(
        exec_info=exec_info,
        content=document.content,
        extraction_instructions=extraction_instructions,
        model_class=model_class,
        model_class_name=model_class_name,
        multiple_items=multiple_items,
        query_metadata=query_metadata,
    )

    # update the collection of extracted results
    display_logger.debug(extracted_obj_list)
    uri = document.original_uri
    if uri is None:
        uri = document.doc_uri
    if uri in return_objs:
        return_objs[uri].append(extracted_obj_list)
    else:
        return_objs[uri] = extracted_obj_list
