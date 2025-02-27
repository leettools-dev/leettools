import json
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.models.model_info import ModelInfoManager
from leettools.common.utils import config_utils, lang_utils, url_utils
from leettools.common.utils.lang_utils import normalize_lang_name
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.core.consts import flow_option
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.display_type import DisplayType
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.chat_query_result import (
    AnswerSource,
    ChatAnswerItem,
    ChatAnswerItemCreate,
    ChatQueryResult,
    ChatQueryResultCreate,
    SourceItem,
)
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo
from leettools.flow.schemas.article import ArticleSection
from leettools.flow.utils.citation_utils import (
    create_reference_section,
    find_all_cited_references,
    reorder_cited_source_items,
    replace_reference_in_result,
)

URL_SEPARATOR = ", "


def get_output_lang(
    exec_info: ExecInfo, query_metadata: Optional[ChatQueryMetadata] = None
) -> Optional[str]:
    """
    Get the output language from the query options or the query metadata.

    The order is:
    * the flow option FLOW_OPTION_OUTPUT_LANGUAGE
    * the query metadata language identified by the intention_detection
    * the lang field set in the exec_info by previous calls

    Args:
    - exec_info: Execution information.
    - query_metadata: Query metadata.

    Returns:
    - The output language, None if not specified.
    """
    display_logger = logger()
    flow_options = exec_info.flow_options

    lang = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_OUTPUT_LANGUAGE,
        default_value=None,
        display_logger=display_logger,
    )
    if lang is not None:
        return normalize_lang_name(lang)

    if query_metadata is not None:
        if query_metadata.language is not None:
            return normalize_lang_name(query_metadata.language)

    if exec_info.output_lang is not None:
        return normalize_lang_name(exec_info.output_lang)

    query = exec_info.target_chat_query_item.query_content
    if query is not None and query != "":
        language = lang_utils.get_language(query)
        if language is not None:
            return normalize_lang_name(language)
    return None


def get_search_lang(
    exec_info: ExecInfo, query_metadata: Optional[ChatQueryMetadata] = None
) -> Optional[str]:
    """
    Get the search language from the query options or the query metadata.

    The order is:
    * the flow option FLOW_OPTION_SEARCH_LANGUAGE
    * the query metadata language identified by the intention_detection
    * the lang field set in the exec_info by previous calls

    Args:
    - exec_info: Execution information.
    - query_metadata: Query metadata.

    Returns:
        The search language, None if not specified.
    """
    flow_options = exec_info.flow_options
    display_logger = exec_info.display_logger

    lang = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_SEARCH_LANGUAGE,
        default_value=None,
        display_logger=display_logger,
    )

    if lang is not None:
        logger().info(
            f"Using language specified in flow_options.{flow_option.FLOW_OPTION_SEARCH_LANGUAGE}: {lang}"
        )
        return normalize_lang_name(lang)

    if query_metadata is not None:
        if query_metadata.language is not None:
            logger().info(f"Using language specified in query_metadata: {lang}")
            return normalize_lang_name(query_metadata.language)

    if exec_info.output_lang is not None:
        logger().info(f"Using search language specified in exec_info: {lang}")
        return normalize_lang_name(exec_info.output_lang)

    logger().info(f"No language specified for search.")
    return None


def get_doc_summaries_for_docsource(
    exec_info: ExecInfo,
    docsource: DocSource,
) -> Tuple[str, List[Document], Dict[str, int]]:
    """
    Return aggregated information for all documents in a docsource.

    Args:
    - exec_info: Execution information.
    - docsource: The docsource to get summaries for.

    Returns:
    - A tuple containing
        * a string that concatenagtes all the document summaries
        * a list of all documents
        * a dictionary of all keywords with their counts
    """

    docsink_store = exec_info.context.get_repo_manager().get_docsink_store()
    document_store = exec_info.context.get_repo_manager().get_document_store()

    org = exec_info.org
    kb = exec_info.kb
    settings = exec_info.context.settings
    display_logger = exec_info.display_logger

    docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)
    all_documents = []
    all_keywords: Dict[str, int] = {}
    document_summaries: str = ""
    for docsink in docsinks:
        documents = document_store.get_documents_for_docsink(org, kb, docsink)
        if len(documents) == 0:
            display_logger.debug(
                f"No documents found for docsink {docsink.docsink_uuid}"
            )
            continue

        # the list should only have one document unless we support
        # multiple versions of the same document in the future
        document = documents[0]
        if document.embed_status != DocSourceStatus.COMPLETED:
            display_logger.info(
                f"Document {document.document_uuid} has not been processed yet."
            )
            continue

        if document.summary() is None:
            display_logger.info(f"Document {document.document_uuid} has no summary.")
            continue

        summary = document.summary()
        if (
            summary.relevance_score is not None
            and summary.relevance_score < settings.RELEVANCE_THRESHOLD
        ):
            display_logger.info(
                f"Document has a low relevance score: {summary.relevance_score}."
                f"[{document.original_uri}]"
            )
            continue

        for keyword in summary.keywords:
            if keyword in all_keywords:
                all_keywords[keyword] += 1
            else:
                all_keywords[keyword] = 1
        all_documents.append(document)
        document_summaries = document_summaries + "\n" + summary.summary
    return document_summaries, all_documents, all_keywords


def create_chat_result_with_sections(
    exec_info: ExecInfo,
    query: str,
    article_type: str,
    sections: List[ArticleSection],
    accumulated_source_items: Dict[str, SourceItem],
) -> ChatQueryResultCreate:
    """
    Create a ChatQueryResultCreate object with the provided sections and source items.

    Args:
    - exec_info: The execution information.
    - query: The query.
    - article_type: The article type.
    - sections: The sections.
    - accumulated_source_items: The accumulated source items.

    Returns:
    - The ChatQueryResultCreate object.
    """

    display_logger = exec_info.display_logger
    chat_query_item = exec_info.target_chat_query_item
    flow_options = exec_info.flow_options

    reference_style = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_REFERENCE_STYLE,
        default_value=flow_option_items.FOI_REFERENCE_STYLE().default_value,
        display_logger=display_logger,
    )

    full_content = ""
    for section in sections:
        full_content += section.content + "\n"
    cited_source_items = find_all_cited_references(
        content=full_content, accumulated_source_items=accumulated_source_items
    )
    display_logger.debug(f"Found {len(cited_source_items)} cited references.")

    index_mapping_old_to_new = reorder_cited_source_items(
        cited_source_items=cited_source_items,
        reference_style=reference_style,
        display_logger=display_logger,
    )

    full_report = ""
    section_index = 1
    caic_sections = []
    for section in sections:
        content, segment_references = replace_reference_in_result(
            result=section.content,
            cited_source_items=cited_source_items,
            index_mapping_old_to_new=index_mapping_old_to_new,
            reference_style=reference_style,
            display_logger=display_logger,
        )
        display_logger.debug(
            f"Section {section.title} has {len(segment_references)} references."
        )
        full_report += full_report + "\n" + f"# {section.title}\n" + content + "\n"
        caic = ChatAnswerItemCreate(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
            answer_content=content,
            answer_plan=section.plan,
            answer_title=section.title,
            position_in_answer=str(section_index),
            answer_score=1.0,
            answer_source_items=segment_references,
            display_type=section.display_type,
            user_data=section.user_data,
        )
        caic_sections.append(caic)
        section_index += 1

    # for every new index, we only need one source item
    existing_references: Dict[int, SourceItem] = {}
    final_source_items: Dict[str, SourceItem] = {}
    for segment_uuid, source_item in cited_source_items.items():
        display_logger.debug(
            f"Segment {segment_uuid} has index {source_item.index} and "
            f"source uri {source_item.answer_source.source_uri}."
        )
        old_index = source_item.index
        new_index = index_mapping_old_to_new.get(old_index)
        source_item.index = new_index
        source_item.answer_source.source_content = (
            # replace [old_index] with [new_index] in the item itself
            source_item.answer_source.source_content.replace(
                f"[{old_index}]", f"[{new_index}]"
            )
        )
        if new_index not in existing_references:
            final_source_items[segment_uuid] = source_item
            existing_references[new_index] = source_item

    reference_section_str = create_reference_section(exec_info, final_source_items)
    full_report = full_report + reference_section_str

    # position 0 saves all the reference lists
    caic_full_report = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content="",  # we do not need the duplicate result in the first item
        answer_plan=None,
        position_in_answer="all",
        answer_title=f"{query}",
        answer_score=1.0,
        answer_source_items=final_source_items,
        user_data=None,
    )

    caic_list = []  # caic short for ChatAnswerItemCreate

    # the first item in the result is the full report
    caic_list.append(caic_full_report)
    caic_list.extend(caic_sections)

    if reference_section_str != "":
        caic_references = ChatAnswerItemCreate(
            chat_id=chat_query_item.chat_id,
            query_id=chat_query_item.query_id,
            answer_content=reference_section_str,
            answer_plan=None,
            answer_title="References",
            position_in_answer=str(section_index),
            answer_score=1.0,
            display_type=DisplayType.REFERENCES,
            user_data=None,
        )
        caic_list.append(caic_references)
        section_index += 1
    else:
        display_logger.debug("No references in the final result.")

    return ChatQueryResultCreate(
        chat_answer_item_create_list=caic_list,
        global_answer_source_items=final_source_items,
        article_type=article_type,
    )


def create_chat_result_for_empty_search(
    exec_info: ExecInfo, query_metadata: ChatQueryMetadata
) -> ChatQueryResultCreate:
    """
    Create a chat result for an empty search.

    Args:
    - exec_info: The execution information.
    - query_metadata: The query metadata.

    Returns:
    - The ChatQueryResultCreate object.
    """

    chat_query_item = exec_info.target_chat_query_item
    display_logger = exec_info.display_logger
    display_logger.warning("No related segments found. Creating an warning message.")

    # TODO: handle the i18n messages in a centralized way
    empty_result_prompt = (
        "Sorry, I am unable to find a related document for the question."
    )
    chat_answer_item_create_list = []
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=empty_result_prompt,
        position_in_answer="all",
        answer_title=exec_info.target_chat_query_item.query_content,
        answer_plan=None,
        answer_score=0,
    )
    chat_answer_item_create_list.append(chat_answer_item_create)
    return ChatQueryResultCreate(
        chat_answer_item_create_list=chat_answer_item_create_list
    )


def create_chat_result_with_manual_msg(
    msg: str, exec_info: ExecInfo, query_metadata: ChatQueryMetadata
) -> ChatQueryResultCreate:
    chat_query_item = exec_info.target_chat_query_item

    chat_answer_item_create_list = []
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=msg,
        answer_plan=None,
        position_in_answer="all",
        answer_score=0,
    )
    # The 0th item is the full report
    chat_answer_item_create_list.append(chat_answer_item_create)

    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=msg,
        answer_plan=None,
        position_in_answer="1",
        answer_title="Results",
        answer_score=1,
    )

    # the 1st item is the detailed section
    chat_answer_item_create_list.append(chat_answer_item_create)
    return ChatQueryResultCreate(
        chat_answer_item_create_list=chat_answer_item_create_list
    )


def create_chat_result_with_table_msg(
    msg: str,
    header: List[str],
    rows: List[Dict[str, any]],
    exec_info: ExecInfo,
    query_metadata: ChatQueryMetadata,
) -> ChatQueryResultCreate:
    """
    Create a chat result with a table message. We need the header and rows to create
    user data so that display can render the table. The msg will be stored as
    the answer content.

    Args:
    - msg: The message to display.
    - header: The header of the table as a list of strings.
    - rows: The rows of the table as a list of records. Each record is a dictionary.
    - exec_info: The execution information.
    - query_metadata: The query metadata.

    Returns:
    - The chat query result.
    """
    chat_query_item = exec_info.target_chat_query_item

    chat_answer_item_create_list = []

    # The 0th item is the full report
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=msg,
        answer_plan=None,
        position_in_answer="all",
        answer_score=0,
    )
    chat_answer_item_create_list.append(chat_answer_item_create)

    # the 1st item is the detailed section
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=msg,
        answer_plan=None,
        position_in_answer="1",
        answer_title="Results",
        answer_score=1,
        display_type=DisplayType.TABLE,
        user_data={"header": header, "rows": rows},
    )
    chat_answer_item_create_list.append(chat_answer_item_create)

    return ChatQueryResultCreate(
        chat_answer_item_create_list=chat_answer_item_create_list
    )


def create_chat_result_with_csv_data(
    header: List[str],
    rows: List[List[Any]],
    exec_info: ExecInfo,
    query_metadata: ChatQueryMetadata,
) -> ChatQueryResultCreate:
    """
    Create a chat result with a csv message. We need the header and rows to create
    the user data so that display can render the csv. The msg will be stored as
    the answer content.

    Args:
    - msg: The message to display.
    - header: The header of the table as a list of strings.
    - rows: The rows of the table as a list of records. Each record is a dictionary.
    - exec_info: The execution information.
    - query_metadata: The query metadata.

    Returns:
    - The chat query result.
    """
    chat_query_item = exec_info.target_chat_query_item

    chat_answer_item_create_list = []

    answer_content = ",".join(header) + "\n"
    for row in rows:
        answer_content += ",".join([str(x) for x in row]) + "\n"

    # The 0th item is the full report
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=answer_content,
        answer_plan=None,
        position_in_answer="all",
        answer_score=0,
    )
    chat_answer_item_create_list.append(chat_answer_item_create)

    # the 1st item is the detailed section
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=answer_content,
        answer_plan=None,
        position_in_answer="1",
        answer_title="Results",
        answer_score=1,
        display_type=DisplayType.CSV,
        user_data={"header": header, "rows": rows},
    )
    chat_answer_item_create_list.append(chat_answer_item_create)

    return ChatQueryResultCreate(
        chat_answer_item_create_list=chat_answer_item_create_list,
        article_type=ArticleType.CSV,
    )


def create_chat_result_with_json_data(
    json_data: Dict[str, Any],
    exec_info: ExecInfo,
    query_metadata: ChatQueryMetadata,
) -> ChatQueryResultCreate:
    """
    Create a chat result with a json message. We need the json data as the
    the user data so that display can render the data as needed. The data will also
    be stored as the answer content.

    Args:
    - json_data: The json data to display.
    - exec_info: The execution information.
    - query_metadata: The query metadata.

    Returns:
    - The chat query result.
    """
    chat_query_item = exec_info.target_chat_query_item

    chat_answer_item_create_list = []

    answer_content = json.dumps(json_data, indent=2)

    # The 0th item is the full report
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=answer_content,
        answer_plan=None,
        position_in_answer="all",
        answer_score=0,
    )
    chat_answer_item_create_list.append(chat_answer_item_create)

    # the 1st item is the detailed section
    chat_answer_item_create = ChatAnswerItemCreate(
        chat_id=chat_query_item.chat_id,
        query_id=chat_query_item.query_id,
        answer_content=answer_content,
        answer_plan=None,
        position_in_answer="1",
        answer_title="Results",
        answer_score=1,
        display_type=DisplayType.JSON,
        user_data={"json_data": json_data},
    )
    chat_answer_item_create_list.append(chat_answer_item_create)

    return ChatQueryResultCreate(
        chat_answer_item_create_list=chat_answer_item_create_list,
        article_type=ArticleType.CSV,
    )


def limit_content(content: str, model_name: str, display_logger: EventLogger) -> str:
    # TODO: the way we need to pass the display_logger around is not ideal
    # TODO: use proper language or tokenzier to get the token count
    context_limit = ModelInfoManager().get_context_size(
        model_name, display_logger=display_logger
    )

    token_per_char = lang_utils.token_per_char_ratio(content)
    token_count = int(len(content) * token_per_char)

    if context_limit > 4000:
        actual_limit = context_limit - 1000
    else:
        actual_limit = context_limit

    if token_count > actual_limit:
        actual_content_len = int(actual_limit / token_per_char)
        display_logger.info(
            f"Estimated token count too long {token_count} > {actual_limit} "
            f"for {len(content)} chars, [{model_name}:{context_limit}]. "
            f"Only using first {actual_content_len} characters."
        )
        content = content[:actual_content_len]
    return content


def generate_example_object(model_class: Type[TypeVar_BaseModel]) -> str:
    example_data_dict = {}
    for name, field in model_class.model_fields.items():
        if field.examples is not None and len(field.examples) > 0:
            example_data_dict[name] = field.examples[0]
        else:
            raise exceptions.ConfigValueException(
                name, "No example provided for field in model."
            )

    example_instance = model_class.model_validate(example_data_dict)
    return example_instance.model_dump_json()


def chat_query_result_to_article(query: str, chat_query_result: ChatQueryResult) -> str:
    """
    Turn a chat query result with multi-section answer into a markdown article.

    Args:
    - query: The query.
    - chat_query_result: The chat query result.

    Returns:
    - The markdown article.
    """
    result_article = ""
    article_type = chat_query_result.article_type
    if article_type != ArticleType.CSV:
        result_article += f"# {query.title()}\n"
    chat_answer_items: List[ChatAnswerItem] = chat_query_result.chat_answer_item_list
    for answer in chat_answer_items:
        if answer.position_in_answer == "all":
            continue
        if answer.answer_score < 0:
            continue
        if answer.answer_title is not None:
            if article_type != ArticleType.CSV:
                result_article += f"## {answer.answer_title}\n"
        result_article += f"{answer.answer_content}\n"
    return result_article


def inference_result_to_answer(
    result_content: str,
    source_items: Dict[str, SourceItem],
    reference_style: str,
    display_logger: Optional[EventLogger] = None,
) -> Tuple[str, Dict[str, SourceItem]]:
    """
    Find all the cited references from the source items, reorder them so that the
    citation numbers are continuous, and replace the references according to the
    reference style.

    Args:
    - result_content: The content to be replaced.
    - source_items: The dict of source items that are actually used in the content.
        they key is the segment uuid, the value is the source item.
    - reference_style: The style of the reference.
    - display_logger: The logger to display the log messages.

    Returns:
    - A tuple containing
        * a markdown formatted content with references replaced
        * a dict of source items that are actually used in the content
    """
    if display_logger is None:
        display_logger = logger()

    cited_source_items = find_all_cited_references(
        content=result_content, accumulated_source_items=source_items
    )

    index_mapping_old_to_new = reorder_cited_source_items(
        cited_source_items=cited_source_items,
        reference_style=reference_style,
        display_logger=display_logger,
    )
    answer_content, reordered_citations = replace_reference_in_result(
        result=result_content,
        cited_source_items=cited_source_items,
        index_mapping_old_to_new=index_mapping_old_to_new,
        reference_style=reference_style,
        display_logger=display_logger,
    )
    return answer_content, reordered_citations


def chat_query_result_to_post(chat_query_result: ChatQueryResult) -> str:
    """
    Turn a chat query result with multi-section answer into a markdown article.

    Args:
        chat_query_result: The chat query result.

    Returns:
        The markdown article.
    """
    result_article = ""
    chat_answer_items: List[ChatAnswerItem] = chat_query_result.chat_answer_item_list
    for answer in chat_answer_items:
        if answer.position_in_answer == "all":
            continue
        if answer.answer_score < 0:
            continue
        result_article += f"{answer.answer_content}\n"
    return result_article


def to_markdown_table(
    instances: List[BaseModel],
    skip_fields: List[str] = [],
    output_fields: Optional[List[str]] = None,
    url_compact_fields: Optional[List[List]] = None,
) -> str:
    """
    Format a list of Pydantic models as a markdown table.

    In the url_compact_urls list, we expect the input field has a list of URLs that
    are separated by comma and space. We will compact each field into the following format:
    [domain](url1), [domain](url2), ...

    Args:
    - instances: The list of Pydantic objects
    - skip_fields: The fields to skip
    - output_fields: The fields to output, none if all fields
    - url_compact_urls: The list of fields that are URLs we should show in compact format
    """

    if not instances:
        return ""

    headers = instances[0].model_fields.keys()
    if skip_fields:
        headers = [header for header in headers if header not in skip_fields]
    if output_fields is not None and len(output_fields) > 0:
        headers = [header for header in headers if header in output_fields]

    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"

    rows = []

    def get_field_value(instance, field) -> str:
        field_value = getattr(instance, field)
        if isinstance(field_value, list):
            if url_compact_fields is not None and field in url_compact_fields:
                field_value_str = URL_SEPARATOR.join(
                    [
                        f"[{url_utils.get_domain_from_url(url)}]({url})"
                        for url in field_value
                    ]
                )
            else:
                field_value_str = ", ".join(field_value)
        elif isinstance(field_value, dict):
            field_value_str = json.dumps(field_value)
        else:
            if url_compact_fields is not None and field in url_compact_fields:
                field_value_str = URL_SEPARATOR.join(
                    [
                        f"[{url_utils.get_domain_from_url(url)}]({url})"
                        for url in str(field_value).split(URL_SEPARATOR)
                    ]
                )
            else:
                field_value_str = str(field_value)
        return field_value_str

    for instance in instances:
        row = (
            "| "
            + " | ".join([get_field_value(instance, field) for field in headers])
            + " |"
        )
        rows.append(row)

    return "\n".join([header_row, separator_row] + rows)


def flatten_results(
    objs_dict: Dict[str, List[TypeVar_BaseModel]]
) -> List[TypeVar_BaseModel]:
    """
    Args:

    - objs_dict:
      The key is the concatenated key fields of the target model.
      The value is the list of objects extracted from the document.

    Returns:
    - One object per key str that has all the fields with the best possible
      value in that field.
    """
    target_list = []
    for key_str in sorted(objs_dict.keys()):
        obj_list = objs_dict[key_str]
        for obj in obj_list:
            target_list.append(obj)
    return target_list


def dedupe_results(
    objs_dict: Dict[str, List[TypeVar_BaseModel]]
) -> Dict[str, TypeVar_BaseModel]:
    """
    Ideally, the process should be:
    1. find all duped keys, combine their records
    2. for each key, find the best record or generate a new record that has the best
    values

    Right now we just return the longest record for each key.

    Args:
    - objs_dict:
        The key is the concatenated key fields of the target model.
        The value is the list of objects extracted from the document.

    Returns:
        A dictionary that has one object per key str that has all the fields with the
        best possible value in that field.
    """

    result = {}
    for key_str in sorted(objs_dict.keys()):
        obj_list = objs_dict[key_str]

        # sort  the list by the length of the object
        obj_list.sort(key=lambda x: len(str(x)))

        # return the longest object
        result[key_str] = obj_list[-1]
    return result
