from typing import List

from pydantic import BaseModel

from leettools.common.logging import logger


class TestModel(BaseModel):
    field1: str
    field2: int


def test_csv_output():
    target_model = TestModel

    data1 = TestModel(field1="test1", field2=1)
    data2 = TestModel(field1="test2", field2=2)
    extracted_objs_dict = {
        "uri1": [data1],
        "uri2": [data2],
    }

    target_output = """original_uri,field1,field2
uri1,test1,1
uri2,test2,2
"""

    display_headers = ["original_uri"]
    display_headers.extend(target_model.model_fields.keys())
    logger().info(f"display_headers: {display_headers}")
    rows_data: List[List] = []
    for doc_original_uri, extracted_objs in extracted_objs_dict.items():
        for obj in extracted_objs:
            row_data = [doc_original_uri]
            row_data.extend(obj.model_dump().values())
            rows_data.append(row_data)

    answer_content = ",".join(display_headers) + "\n"
    for row in rows_data:
        answer_content += ",".join([str(x) for x in row]) + "\n"

    assert target_output == answer_content
