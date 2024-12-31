import leettools.flow.utils.citation_utils
from leettools.common.logging import logger
from leettools.core.schemas.chat_query_result import AnswerSource, SourceItem


def test_replace_reference_in_result_full():

    content = "This is a test content [2] with a reference"
    accumulated_source_items = {
        "segment_uuid_1": SourceItem(
            index=1,
            source_segment_id="segment_uuid_1",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_1",
                source_uri="http://source_uri_1",
                source_content="This is the answer item 1",
                score=1.0,
                position_in_doc="all",
                start_offset=0,
                end_offset=1,
                original_uri="http://original_uri_1",
            ),
        ),
        "segment_uuid_2": SourceItem(
            index=2,
            source_segment_id="segment_uuid_2",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_2",
                source_uri="http://source_uri_2",
                source_content="This is the answer item 2",
                score=1.0,
                position_in_doc="all",
                start_offset=0,
                end_offset=1,
                original_uri="http://original_uri_2",
            ),
        ),
    }

    cited_source_items = leettools.flow.utils.citation_utils.find_all_cited_references(
        content, accumulated_source_items
    )

    assert len(cited_source_items) == 1
    assert cited_source_items["segment_uuid_2"].source_segment_id == "segment_uuid_2"

    result, segment_references = (
        leettools.flow.utils.citation_utils.replace_reference_in_result(
            result=content,
            cited_source_items=cited_source_items,
            index_mapping_old_to_new={2: 1},
            reference_style="full",
            display_logger=logger(),
        )
    )
    assert result == "This is a test content [[1](#reference-1)] with a reference"
    assert len(segment_references) == 1
    assert segment_references["segment_uuid_2"].source_segment_id == "segment_uuid_2"


def test_replace_reference_in_result_default():

    content = "This is a test content [2] with a reference"
    accumulated_source_items = {
        "segment_uuid_1": SourceItem(
            index=1,
            source_segment_id="segment_uuid_1",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_1",
                source_uri="http://source_uri_1",
                source_content="This is the answer item 1",
                score=1.0,
                position_in_doc="all",
                start_offset=0,
                end_offset=1,
                original_uri="http://original_uri_1",
            ),
        ),
        "segment_uuid_2": SourceItem(
            index=2,
            source_segment_id="segment_uuid_2",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_2",
                source_uri="http://source_uri_2",
                source_content="This is the answer item 2",
                score=1.0,
                position_in_doc="all",
                start_offset=0,
                end_offset=1,
                original_uri="http://original_uri_2",
            ),
        ),
    }

    cited_source_items = leettools.flow.utils.citation_utils.find_all_cited_references(
        content, accumulated_source_items
    )

    assert len(cited_source_items) == 1
    assert cited_source_items["segment_uuid_2"].source_segment_id == "segment_uuid_2"

    result, segment_references = (
        leettools.flow.utils.citation_utils.replace_reference_in_result(
            result=content,
            cited_source_items=cited_source_items,
            index_mapping_old_to_new={2: 1},
            reference_style="default",
            display_logger=logger(),
        )
    )
    assert result == "This is a test content [1] with a reference"
    assert len(segment_references) == 1
    assert segment_references["segment_uuid_2"].source_segment_id == "segment_uuid_2"
