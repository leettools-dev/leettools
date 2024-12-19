from unittest.mock import patch

from leettools.context_manager import Context, ContextManager
from leettools.eds.pipeline.convert._impl import converter_utils


def test_extract_title():
    text = "Prodcut Name\nVersion 1.0\nManual"
    context = ContextManager().get_context()  # type: Context
    actual_result = converter_utils.extract_title(context.settings, text)
    assert actual_result == ""


def test_parse_table():
    table_text = "| 1.1.1 introduction name | ..."
    context = ContextManager().get_context()  # type: Context
    actual_result = converter_utils.parse_table(context.settings, table_text)
    assert actual_result == "| 1.1.1 introduction name | ..."
