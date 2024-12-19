from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
)
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling_core.types.doc import PictureItem, TableItem

from leettools.common.logging import logger
from leettools.eds.pipeline.convert.parser import AbstractParser
from leettools.settings import SystemSettings


class ParserDocling(AbstractParser):
    """Parse file content and convert it to Markdown using Docling parser."""

    def __init__(self, settings: SystemSettings):
        super().__init__()
        self.settings = settings

        # Move initialization to constructor
        # TODO: make these parameters configurable
        IMAGE_RESOLUTION_SCALE = 2.0
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
        pipeline_options.generate_page_images = True
        pipeline_options.generate_table_images = True
        pipeline_options.generate_picture_images = True

        # Initialize converter for this instance
        self.doc_converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.DOCX,
                InputFormat.PPTX,
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    pipeline_cls=StandardPdfPipeline,
                    backend=PyPdfiumDocumentBackend,
                ),
                InputFormat.DOCX: WordFormatOption(pipeline_cls=SimplePipeline),
            },
        )

    def _convert(self, filepath: str) -> str:
        try:
            # Use instance converter instead of module-level one
            result = self.doc_converter.convert(filepath)
            output_dir = Path(filepath).parent
            doc_filename = Path(filepath).stem
            doc_filename = doc_filename.split(".")[0]

            # Save page images
            for page_no, page in result.document.pages.items():
                page_no = page.page_no
                page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
                with page_image_filename.open("wb") as fp:
                    page.image.pil_image.save(fp, format="PNG")

            # Save images of figures and tables
            table_counter = 0
            picture_counter = 0
            for element, _level in result.document.iterate_items():
                if isinstance(element, TableItem):
                    table_counter += 1
                    element_image_filename = (
                        output_dir / f"{doc_filename}-table-{table_counter}.png"
                    )
                    with element_image_filename.open("wb") as fp:
                        element.image.pil_image.save(fp, "PNG")

                if isinstance(element, PictureItem):
                    picture_counter += 1
                    element_image_filename = (
                        output_dir / f"{doc_filename}-picture-{picture_counter}.png"
                    )
                    with element_image_filename.open("wb") as fp:
                        element.image.pil_image.save(fp, "PNG")

            return result.document.export_to_markdown()
        except Exception as exc:
            logger().error(f"Failed to parser {filepath}, error: {exc}")
            return ""

    def docx2md(self, docx_filepath: str) -> str:
        """
        Parses the DOCX and returns the content in markdown format.

        Args:
            docx_filepath: The path to the DOCX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting DOCX to markdown: {docx_filepath}")
        return self._convert(docx_filepath)

    def pdf2md(self, pdf_filepath: str) -> str:
        """
        Parses the PDF and returns the content in markdown format.

        Args:
            pdf_filepath: The path to the PDF file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting PDF to markdown: {pdf_filepath}")
        return self._convert(pdf_filepath)

    def pptx2md(self, pptx_filepath: str) -> str:
        """
        Parses the PPTX and returns the content in markdown format.

        Args:
            pptx_filepath: The path to the PPTX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting PPTX to markdown: {pptx_filepath}")
        return self._convert(pptx_filepath)

    def xlsx2md(self, xlsx_filepath: str) -> str:
        """
        Parses the XLSX and returns the content in markdown format.

        Args:
            xlsx_filepath: The path to the XLSX file.

        Returns:
            The content in markdown format.
        """
        # not supported yet
        logger().error(
            f"XLSX to markdown conversion is not supported yet: {xlsx_filepath}"
        )
        return ""
