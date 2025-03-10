from typing import Optional

import pytest
from pydantic import BaseModel, Field

from leettools.common.logging import logger
from leettools.core.schemas.chat_query_result import AnswerSource, SourceItem
from leettools.flow.utils import flow_utils
from leettools.flow.utils.flow_utils import _replace_think_section_in_result


def test_output_util():

    class TestClass(BaseModel):
        name: str = Field(..., description="The name of the variable.")
        description: Optional[str] = Field(
            None, description="The description of the variable."
        )
        default_value: Optional[str] = Field(
            None, description="The default value of the variable."
        )
        value_type: Optional[str] = Field(
            "str",
            description="The type of the value,"
            "currently support str, int, float, bool.",
        )
        urls: Optional[list[str]] = Field(
            None, description="The list of URLs for the variable."
        )

        urls_as_str: Optional[str] = Field(
            None, description="The list of URLs for the variable."
        )

    obj1 = TestClass(
        name="test1",
        description="description of test1",
        default_value="test2",
        value_type="str",
        urls=["http://www.url11.com/test", "http://url12.gov.br/test"],
        urls_as_str="http://www.url11.com/test, http://url12.gov.br/test",
    )
    obj2 = TestClass(
        name="test2",
        description="description2",
        default_value="test2",
        value_type="str",
        urls=["http://url2.com"],
        urls_as_str="http://url2.com",
    )

    output = flow_utils.to_markdown_table(
        instances=[obj1, obj2],
        skip_fields=["value_type", "default_value"],
        output_fields=["name", "description"],
    )
    expected_output = """| name | description |
| --- | --- |
| test1 | description of test1 |
| test2 | description2 |"""
    assert output == expected_output

    output2 = flow_utils.to_markdown_table(
        instances=[obj1, obj2],
        output_fields=["name", "description", "urls"],
        url_compact_fields=["urls"],
    )
    expected_output2 = """| name | description | urls |
| --- | --- | --- |
| test1 | description of test1 | [url11.com](http://www.url11.com/test), [url12.gov.br](http://url12.gov.br/test) |
| test2 | description2 | [url2.com](http://url2.com) |"""
    assert output2 == expected_output2

    output3 = flow_utils.to_markdown_table(
        instances=[obj1, obj2],
        output_fields=["name", "description", "urls_as_str"],
        url_compact_fields=["urls_as_str"],
    )
    expected_output3 = """| name | description | urls_as_str |
| --- | --- | --- |
| test1 | description of test1 | [url11.com](http://www.url11.com/test), [url12.gov.br](http://url12.gov.br/test) |
| test2 | description2 | [url2.com](http://url2.com) |"""

    print(output3)
    assert output3 == expected_output3


def test_inference_result_to_answer_full():

    content = "This is a test content [3] with two references [1]."
    source_items = {
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
        "segment_uuid_3": SourceItem(
            index=3,
            source_segment_id="segment_uuid_3",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_3",
                source_uri="http://source_uri_3",
                source_content="This is the answer item 3",
                score=1.0,
                position_in_doc="all",
                start_offset=0,
                end_offset=1,
                original_uri="http://original_uri_3",
            ),
        ),
    }

    updated_content, used_source_items = flow_utils.inference_result_to_answer(
        result_content=content,
        source_items=source_items,
        reference_style="full",
        display_logger=logger(),
    )

    assert (
        updated_content
        == "This is a test content [[2](#reference-2)] with two references [[1](#reference-1)]."
    )

    assert len(used_source_items) == 2
    assert used_source_items["segment_uuid_1"].source_segment_id == "segment_uuid_1"
    assert used_source_items["segment_uuid_1"].index == 1
    assert used_source_items["segment_uuid_3"].source_segment_id == "segment_uuid_3"
    assert used_source_items["segment_uuid_3"].index == 2


def test_inference_result_to_answer_default():

    content = "test content [3][4][3] references [1]. Same as 3 [4]. Same as 1 [5][5]."

    source_items = {
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
        "segment_uuid_3": SourceItem(
            index=3,
            source_segment_id="segment_uuid_3",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_3",
                source_uri="http://source_uri_3",
                source_content="This is the answer item 3",
                score=1.0,
                position_in_doc="all",
                start_offset=0,
                end_offset=1,
                original_uri="http://original_uri_3",
            ),
        ),
        "segment_uuid_4": SourceItem(
            index=4,
            source_segment_id="segment_uuid_4",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_3",
                source_uri="http://source_uri_3",
                source_content="This is the answer item 4",
                score=1.0,
                position_in_doc="all",
                start_offset=2,
                end_offset=3,
                original_uri="http://original_uri_3",
            ),
        ),
        "segment_uuid_5": SourceItem(
            index=5,
            source_segment_id="segment_uuid_5",
            answer_source=AnswerSource(
                source_document_uuid="source_doc_id_1",
                source_uri="http://source_uri_1",
                source_content="This is the answer item 5",
                score=1.0,
                position_in_doc="all",
                start_offset=5,
                end_offset=6,
                original_uri="http://original_uri_1",
            ),
        ),
    }

    updated_content, used_source_items = flow_utils.inference_result_to_answer(
        result_content=content,
        source_items=source_items,
        reference_style="default",
        display_logger=logger(),
    )

    assert (
        updated_content
        == "test content [2] references [1]. Same as 3 [2]. Same as 1 [1]."
    )

    assert len(used_source_items) == 2
    assert used_source_items["segment_uuid_1"].source_segment_id == "segment_uuid_1"
    assert used_source_items["segment_uuid_1"].index == 1
    assert used_source_items["segment_uuid_3"].source_segment_id == "segment_uuid_3"
    assert used_source_items["segment_uuid_3"].index == 2


def test_replace_think_section_in_result():
    """Test replacing think sections in content with HTML comments."""
    display_logger = logger()

    # Test case 1: Content with think section at the beginning
    content_with_think = (
        "<think>This is a thinking process</think>Here is the actual content"
    )
    expected_with_think = (
        "<!--think>This is a thinking process</think-->Here is the actual content"
    )
    result = _replace_think_section_in_result(content_with_think, display_logger)
    assert result == expected_with_think

    # Test case 2: Content without think section
    content_without_think = "This is just regular content"
    result = _replace_think_section_in_result(content_without_think, display_logger)
    assert result == content_without_think

    # Test case 3: Content with malformed think section (no end tag)
    content_malformed = "<think>This is incomplete content"
    result = _replace_think_section_in_result(content_malformed, display_logger)
    assert result == content_malformed

    # Test case 4: Content with think section not at the beginning
    content_think_middle = "Some content before <think>thinking</think>content after"
    result = _replace_think_section_in_result(content_think_middle, display_logger)
    assert result == content_think_middle

    # Test case 5: Empty content
    empty_content = ""
    result = _replace_think_section_in_result(empty_content, display_logger)
    assert result == empty_content

    # Test case 6: Content with multiple think sections (only first should be replaced)
    content_multiple_think = (
        "<think>First think</think>middle<think>Second think</think>"
    )
    expected_multiple = (
        "<!--think>First think</think-->middle<think>Second think</think>"
    )
    result = _replace_think_section_in_result(content_multiple_think, display_logger)
    assert result == expected_multiple
