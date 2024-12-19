from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from docling_core.types.doc import PictureItem, TableItem

from leettools.eds.pipeline.convert._impl.parser_docling import ParserDocling
from leettools.settings import SystemSettings


@pytest.fixture
def settings():
    return SystemSettings().initialize()


@pytest.fixture
def docling_parser(settings):
    return ParserDocling(settings)


@pytest.fixture
def mock_document():
    doc = Mock()
    doc.pages = {
        1: Mock(page_no=1, image=Mock(pil_image=Mock())),
        2: Mock(page_no=2, image=Mock(pil_image=Mock())),
    }

    # Create mock items for iteration
    table_item = Mock(spec=TableItem)
    table_item.image = Mock(pil_image=Mock())
    picture_item = Mock(spec=PictureItem)
    picture_item.image = Mock(pil_image=Mock())

    doc.iterate_items.return_value = [(table_item, 1), (picture_item, 1)]
    doc.export_to_markdown.return_value = "# Test Markdown"
    return doc


@pytest.fixture
def mock_conversion_result(mock_document):
    result = Mock()
    result.document = mock_document
    return result


class TestDoclingParser:

    @pytest.mark.parametrize(
        "method,file_path",
        [
            ("pdf2md", "test.pdf"),
            ("docx2md", "test.docx"),
            ("pptx2md", "test.pptx"),
            ("xlsx2md", "test.xlsx"),
        ],
    )
    def test_conversion_methods(self, docling_parser, method, file_path, tmp_path):
        if method == "xlsx2md":
            result = getattr(docling_parser, method)(file_path)
            assert result == ""
        else:
            test_file = tmp_path / file_path
            test_file.touch()

            with patch.object(docling_parser, "doc_converter") as mock_converter:
                mock_result = Mock()
                mock_doc = Mock()
                mock_doc.pages = {}
                mock_doc.iterate_items.return_value = []
                mock_doc.export_to_markdown.return_value = "# Test Markdown"
                mock_result.document = mock_doc
                mock_converter.convert.return_value = mock_result

                result = getattr(docling_parser, method)(str(test_file))
                mock_converter.convert.assert_called_once_with(str(test_file))
                assert result == "# Test Markdown"

    def test_successful_conversion(
        self, docling_parser, mock_conversion_result, tmp_path
    ):
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        with patch.object(docling_parser, "doc_converter") as mock_converter:
            mock_converter.convert.return_value = mock_conversion_result
            result = docling_parser._convert(str(test_file))
            assert result == "# Test Markdown"
            mock_conversion_result.document.export_to_markdown.assert_called_once()

    def test_failed_conversion(self, docling_parser):
        # Setup
        with patch.object(docling_parser, "doc_converter") as mock_converter:
            mock_converter.convert.side_effect = Exception("Conversion failed")

            # Execute
            result = docling_parser._convert("test.pdf")

            # Verify
            assert result == ""

    def test_image_saving(self, docling_parser, mock_conversion_result, tmp_path):
        # Setup
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        with patch.object(docling_parser, "doc_converter") as mock_converter:
            mock_converter.convert.return_value = mock_conversion_result

            # Execute
            docling_parser._convert(str(test_file))

            # Verify page images were saved
            for page in mock_conversion_result.document.pages.values():
                page.image.pil_image.save.assert_called()

            # Verify table and picture images were saved
            for item, _ in mock_conversion_result.document.iterate_items():
                item.image.pil_image.save.assert_called()

    def test_initialization(self, settings):
        parser = ParserDocling(settings)
        assert parser.settings == settings
