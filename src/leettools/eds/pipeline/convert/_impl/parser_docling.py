from pathlib import Path
from typing import Optional

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

    def _convert(self, filepath: str, target_path: Optional[Path] = None) -> str:
        try:
            # Use instance converter instead of module-level one
            result = self.doc_converter.convert(filepath)
            if target_path:
                output_dir = Path(target_path).parent
            else:
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

            content = result.document.export_to_markdown()
            if target_path:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
            return content
        except Exception as exc:
            logger().error(f"Failed to parse {filepath}, error: {exc}")
            return ""

    def docx2md(self, docx_filepath: str, target_path: Optional[Path] = None) -> str:
        logger().debug(f"Converting DOCX to markdown: {docx_filepath}")
        return self._convert(docx_filepath, target_path)

    def pdf2md(self, pdf_filepath: str, target_path: Optional[Path] = None) -> str:
        logger().debug(f"Converting PDF to markdown: {pdf_filepath}")
        return self._convert(pdf_filepath, target_path)

    def pptx2md(self, pptx_filepath: str, target_path: Optional[Path] = None) -> str:
        logger().debug(f"Converting PPTX to markdown: {pptx_filepath}")
        return self._convert(pptx_filepath, target_path)

    def xlsx2md(self, xlsx_filepath: str, target_path: Optional[Path] = None) -> str:
        # not supported yet
        logger().error(
            f"XLSX to markdown conversion is not supported yet: {xlsx_filepath}"
        )
        return ""
