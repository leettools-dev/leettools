import os

import pytest

from leettools.context_manager import Context, ContextManager


@pytest.mark.skip(reason="Temporarily disabled because unstructured is not installed")
def test_parse_pdf():
    from leettools.eds.pipeline.convert._impl.parser_unstructured import (
        ParserUnstructured,
    )

    script_dir = os.path.dirname(os.path.realpath(__file__))

    context = ContextManager().get_context()  # type: Context
    pdf_parser = ParserUnstructured(context.settings)
    expected_result = """

Title 1

col1 vaue1 col2 value2

Text 3

"""
    actual_result = pdf_parser.pdf2md(script_dir + "/test_pdf_2_md.pdf")
    assert actual_result == expected_result
