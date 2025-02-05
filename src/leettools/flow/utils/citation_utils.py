import re
import urllib
from typing import Dict, Set, Tuple

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.core.schemas.chat_query_result import SourceItem
from leettools.eds.pipeline.split.splitter import remove_heading_from_content
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo


def find_all_cited_references(
    content: str, accumulated_source_items: Dict[str, SourceItem]
) -> Dict[str, SourceItem]:
    """
    Find all the cited references in the content and return the source items.

    Args:
    - content: The content to search for references.
    - accumulated_source_items: The accumulated source items.

    Returns:
    - A dictionary of the source items that are acutally used in the content.
    """
    cited_references: Dict[str, SourceItem] = {}
    for segment_uuid, source_item in accumulated_source_items.items():
        # we probably can just do a replace all at once using regex
        # but we do not want to add references to no-existing references
        index = source_item.index
        pattern = re.escape(f"[{index}]")
        if re.search(pattern, content) != None:
            cited_references[segment_uuid] = source_item
    return cited_references


def create_reference_section(
    exec_info: ExecInfo, cited_source_items: Dict[str, SourceItem]
) -> str:
    """
    Create a reference section based on the provided execution information and
    cited source items. Note that the content itself should be created using the
    same reference style, otherwise the references will not be matched.

    * If the reference_style is news, no local references will be created and all
    references from the same URL will be aggregated together.
    * If the reference_style is full, the exact location of the markdown segment will
    be shown in the reference section. Since it is a referece to a service endpoint
    that serves the document, the URL will be shown as well.
    * In the default reference style, one document may be referenced multiple times in
    the content, and will be listed in the reference section only once.

    Args:
    - exec_info (ExecInfo): The execution information.
    - cited_source_items (Dict[str, SourceItem]): The accumulated source items.

    Returns:
    - str: The generated reference section.

    """
    reference_section = ""
    if cited_source_items is None or len(cited_source_items) == 0:
        return reference_section

    flow_options = exec_info.flow_options
    display_logger = exec_info.display_logger

    # TODO: make sure the reference style show up in the options
    reference_style = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_REFERENCE_STYLE,
        default_value=flow_option_items.FOI_REFERENCE_STYLE().default_value,
        display_logger=display_logger,
    )

    display_mode = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_DISPLAY_MODE,
        default_value="cli",
        display_logger=display_logger,
    )

    if display_mode == "cli":
        newlines = "\n"
    elif display_mode == "web":
        newlines = "\n\n"
    else:
        display_logger.warning(
            f"Unknown display mode {display_mode}. Use the default cli mode."
        )
        newlines = "\n"

    if reference_style == "news":
        # for news, we aggregate all the references from the same document together
        uris: Set[str] = set()
        for source_item in cited_source_items.values():
            # we need to aggregate same reference together
            answer_source = source_item.answer_source
            original_uri = answer_source.original_uri
            if original_uri is not None:
                if original_uri.startswith("http"):
                    uris.add(original_uri)
        index = 0
        for uri in uris:
            index += 1
            # We can add emojis here
            # the index is not shown in the article so the order does not matter
            reference_section += f"[{index}] [{uri}]({uri}){newlines}"
        return reference_section

    if reference_style == "full":
        # the full style will have the exact location of the markdown segment
        for source_item in cited_source_items.values():
            index = source_item.index
            answer_source = source_item.answer_source

            doc_uuid = answer_source.source_document_uuid
            doc_uri = answer_source.source_uri
            original_uri = answer_source.original_uri
            start_offset = answer_source.start_offset
            end_offset = answer_source.end_offset

            source_content = source_item.answer_source.source_content
            source_content = remove_heading_from_content(source_content)
            # remove existing [x] from the content if it exists
            source_content = re.sub(r"^\s*\[\d+\]\s*", "", source_content)
            # truncate the content to 30 characters
            source_content = source_content[:30].replace("\n", " ") + "..."

            file_link = (
                f"/#/file?kbName={urllib.parse.quote(exec_info.kb.name)}&doc_uuid={doc_uuid}"
                f"&start_offset={start_offset}&end_offset={end_offset}"
            )
            reference_section += (
                f'<a id="reference-{index}"></a> [{index}] '
                f"[{source_content}]({file_link}){newlines}"
            )
            if original_uri is not None:
                if original_uri.startswith("http"):
                    reference_section += f"[{original_uri}]({original_uri})\n{newlines}"
                elif original_uri.startswith("/app/"):
                    uri_link = f"/#/file?uri={original_uri}"
                    reference_section += f"[{original_uri}]({uri_link})\n{newlines}"
                else:
                    reference_section += f"[{original_uri}]({original_uri})\n{newlines}"
            else:
                reference_section += f"{newlines}"

        return reference_section

    if reference_style != "default":
        if reference_style == None or reference_style == "":
            display_logger.debug("No reference_style specified. Using default.")
        else:
            display_logger.info(
                f"Unknown reference style {reference_style}. Use the default style."
            )
        reference_style = "default"

    # for default style, we just show the cited items with a simple link
    for source_item in cited_source_items.values():
        index = source_item.index
        answer_source = source_item.answer_source

        doc_uuid = answer_source.source_document_uuid
        doc_uri = answer_source.source_uri
        original_uri = answer_source.original_uri
        start_offset = answer_source.start_offset
        end_offset = answer_source.end_offset

        if original_uri is not None:
            uri = original_uri
        else:
            uri = doc_uri

        reference_section += f"[{index}] [{uri}]({uri}){newlines}"
    return reference_section


def reorder_cited_source_items(
    cited_source_items: Dict[str, SourceItem],
    reference_style: str,
    display_logger: EventLogger,
) -> Dict[int, int]:
    # index mapping from the old index to the new index
    index_mapping_old_to_new: Dict[int, int] = {}

    if reference_style == "full":
        reorder_id = 1
        for segment_uuid in cited_source_items.keys():
            source_item = cited_source_items[segment_uuid]
            old_index = source_item.index
            new_index = reorder_id
            index_mapping_old_to_new[old_index] = new_index
            reorder_id += 1
    elif reference_style == "news":
        reorder_id = 1
        # the key is the uri, the value is the new index
        uri_map: Dict[str, int] = {}
        for segment_uuid in cited_source_items.keys():
            source_item = cited_source_items[segment_uuid]
            old_index = source_item.index
            uri = source_item.answer_source.original_uri
            if uri in uri_map:
                new_index = uri_map[uri]
                index_mapping_old_to_new[old_index] = new_index
            else:
                new_index = reorder_id
                uri_map[uri] = new_index
                index_mapping_old_to_new[old_index] = new_index
                reorder_id += 1
    else:
        if reference_style != "default":
            if reference_style == None or reference_style == "":
                display_logger.debug("No reference_style specified. Using default.")
            else:
                display_logger.info(
                    f"Unknown reference style {reference_style}. Use the default style."
                )
            reference_style = "default"
        # index mapping from the old index to the new index
        reorder_id = 1
        # the key is the uri, the value is the new index
        uri_map: Dict[str, int] = {}
        for segment_uuid in cited_source_items.keys():
            source_item = cited_source_items[segment_uuid]
            old_index = source_item.index
            uri = source_item.answer_source.original_uri

            if uri in uri_map:
                new_index = uri_map[uri]
                index_mapping_old_to_new[old_index] = new_index
            else:
                new_index = reorder_id
                uri_map[uri] = new_index
                index_mapping_old_to_new[old_index] = new_index
                reorder_id += 1
    return index_mapping_old_to_new


def replace_reference_in_result(
    result: str,
    cited_source_items: Dict[str, SourceItem],
    index_mapping_old_to_new: Dict[int, int],
    reference_style: str,
    display_logger: EventLogger,
) -> Tuple[str, Dict[str, SourceItem]]:
    """
    Replace all the references in the result str in the format of [x] into a markdown
    format of a link to the source item at the end of the content. If the reference
    is a web page, the URL will be added in the reference list.

    args:
    - result: the content to be replaced
    - cited_source_items: the dict of actual cited source items, the key is the segment uuid
    - index_mapping: the mapping of the old index to the old index
    - reference_style: the style of the reference, default is use both exact location
           of the markdown segment and the original URL, news is only the URL.

    returns:
    - a markdown formatted content with references replaced
    - a dict of source items that are actually used in the content
    """
    section_references: Dict[str, SourceItem] = {}

    # for any style, we need only one reference for each index number
    existing_references: Dict[int, SourceItem] = {}

    for segment_uuid, source_item in cited_source_items.items():
        old_index = source_item.index
        pattern = re.escape(f"[{old_index}]")
        if re.search(pattern, result) == None:
            continue

        new_index = index_mapping_old_to_new.get(old_index)
        if new_index is None:
            raise exceptions.UnexpectedCaseException(
                f"Index {old_index} not found in the index mapping, which should not happen."
            )

        section_cited_item = source_item.model_copy(deep=False)
        section_cited_item.index = new_index
        section_cited_item.answer_source.source_content = (
            # replace [old_index] with [new_index] in the item itself
            source_item.answer_source.source_content.replace(
                f"[{old_index}]", f"[{new_index}]"
            )
        )

        if new_index not in existing_references:
            section_references[segment_uuid] = section_cited_item
            existing_references[new_index] = section_cited_item

        if reference_style == "full":
            replacement = f"[[{new_index}_XYZUVW](#reference-{new_index})]"
        elif reference_style == "news":
            replacement = ""
        else:
            if reference_style != "default":
                if reference_style == None or reference_style == "":
                    display_logger.debug("No reference_style specified. Using default.")
                else:
                    display_logger.info(
                        f"Unknown reference style {reference_style}. Use the default style."
                    )
                reference_style = "default"
            replacement = f"[{new_index}_XYZUVW]"
        result = re.sub(pattern, replacement, result)

    for new_index in index_mapping_old_to_new.values():
        pattern = re.escape(f"[{new_index}_XYZUVW]")
        replacement = f"[{new_index}]"
        result = re.sub(pattern, replacement, result)
        if reference_style == "default":
            pattern = re.escape(f"[{new_index}][{new_index}]")
            replacement = f"[{new_index}]"
            while re.search(pattern, result) != None:
                result = re.sub(pattern, replacement, result)

    return result, section_references
