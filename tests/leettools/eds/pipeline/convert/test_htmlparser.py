""" Tests for the HTML to Markdown parser. """

import pytest

from leettools.eds.pipeline.convert._impl.parser_html import ParserHTML


@pytest.fixture
def html_parser():
    return ParserHTML()


def test_parse_html_content(html_parser: ParserHTML):
    html_content = (
        "<html><body><h1>Title with a head</h1><p>Paragraph 1 as 1</p>"
        "<p>Paragraph 2 as 1</p></body></html>"
    )

    expected_result = (
        "# Title with a head Paragraph 1 as 1 Paragraph 2 as 1\n\n## Content"
    )

    actual_result = html_parser.parse_html_content(html_content)
    assert actual_result == expected_result


def test_parse_html(html_parser: ParserHTML, tmp_path):
    html_file = tmp_path / "test.html"
    html_file.write_text(
        "<html><body><h1>Title with a head</h1>"
        "<p>Paragraph 1 as 1</p><p>Paragraph 2 as 1</p></body></html>"
    )
    expected_result = "# Title with a head\n\nParagraph 1 as 1\n\nParagraph 2 as 1\n\n"
    actual_result = html_parser.html2md(str(html_file))
    assert actual_result == expected_result


def test_filter_and_group_paragraphs_with_headings(html_parser):
    text = "Line 1 Line 1\n\nLine 2 Line 2\n\nLine 3 Line 3"
    expected_result = (
        "# Line 1 Line 1\n\n## Content\n\n" "Line 2 Line 2\n\nLine 3 Line 3"
    )
    actual_result = html_parser._filter_and_group_paragraphs_with_headings(text)
    assert actual_result == expected_result


if __name__ == "__main__":
    pytest.main()
