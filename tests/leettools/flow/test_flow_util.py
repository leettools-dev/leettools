from typing import Optional

from pydantic import BaseModel, Field

from leettools.core.schemas.chat_query_result import AnswerSource, SourceItem
from leettools.flow.utils import flow_util


def test_replace_reference_in_result():

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

    result, segment_references = flow_util.replace_reference_in_result(
        result=content,
        cited_source_items=accumulated_source_items,
        index_mapping={},
        reference_style="default",
    )
    assert result == "This is a test content [[2](#reference-2)] with a reference"
    assert len(segment_references) == 1
    assert segment_references["segment_uuid_2"].source_segment_id == "segment_uuid_2"

    result, segment_references = flow_util.replace_reference_in_result(
        result=content,
        cited_source_items=accumulated_source_items,
        index_mapping={2: 2},
        reference_style="default",
    )
    assert result == "This is a test content [[2](#reference-2)] with a reference"
    assert len(segment_references) == 1
    assert segment_references["segment_uuid_2"].source_segment_id == "segment_uuid_2"


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

    output = flow_util.to_markdown_table(
        instances=[obj1, obj2],
        skip_fields=["value_type", "default_value"],
        output_fields=["name", "description"],
    )
    expected_output = """| name | description |
| --- | --- |
| test1 | description of test1 |
| test2 | description2 |"""
    assert output == expected_output

    output2 = flow_util.to_markdown_table(
        instances=[obj1, obj2],
        output_fields=["name", "description", "urls"],
        url_compact_fields=["urls"],
    )
    expected_output2 = """| name | description | urls |
| --- | --- | --- |
| test1 | description of test1 | [url11.com](http://www.url11.com/test), [url12.gov.br](http://url12.gov.br/test) |
| test2 | description2 | [url2.com](http://url2.com) |"""
    assert output2 == expected_output2

    output3 = flow_util.to_markdown_table(
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
