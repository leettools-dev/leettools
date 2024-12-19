from llmsherpa.readers import Document

from leettools.context_manager import Context, ContextManager
from leettools.eds.pipeline.convert._impl.parser_llmsherpa import ParserLLMSherpa


def test_convert_line_to_markdown():
    context = ContextManager().get_context()  # type: Context

    layout_pdf_parser = ParserLLMSherpa(context.settings)
    line = "SECTION 1:"
    expected_result = "# 1 "
    actual_result = layout_pdf_parser._convert_line_to_markdown(line)
    assert actual_result == expected_result

    line = "1.1.1 introduction name"
    expected_result = "### 1.1.1 introduction name"
    actual_result = layout_pdf_parser._convert_line_to_markdown(line)
    assert actual_result == expected_result

    line = "This is a paragraph."
    expected_result = "This is a paragraph."
    actual_result = layout_pdf_parser._convert_line_to_markdown(line)
    assert actual_result == expected_result


def test_traversal_doc():
    context = ContextManager().get_context()  # type: Context
    layout_pdf_parser = ParserLLMSherpa(context.settings)
    pdf_json = [
        {
            "block_class": "cls_1",
            "block_idx": 0,
            "level": 0,
            "page_idx": 0,
            "sentences": ["Header 1"],
            "tag": "header",
        },
        {
            "block_class": "cls_3",
            "block_idx": 1,
            "level": 0,
            "page_idx": 0,
            "sentences": [
                "Para 2",
            ],
            "tag": "para",
        },
        {
            "block_class": "cls_5",
            "block_idx": 2,
            "left": 102.0,
            "level": 1,
            "name": "HDFS Architecture Guide",
            "page_idx": 0,
            "table_rows": [
                {
                    "block_idx": 2,
                    "cells": [{"cell_value": "Cell 1"}],
                    "type": "table_data_row",
                }
            ],
            "tag": "table",
            "top": 266.2,
        },
        {
            "block_class": "cls_8",
            "block_idx": 50,
            "level": 1,
            "page_idx": 3,
            "sentences": ["Item 1"],
            "tag": "list_item",
        },
    ]
    block = Document(pdf_json)

    expected_result = "Header 1\n\nPara 2\n\n | Cell 1\n\n\n<li>Item 1</li>\n\n"
    actual_result = layout_pdf_parser._traversal_doc(block.root_node)
    assert actual_result == expected_result
