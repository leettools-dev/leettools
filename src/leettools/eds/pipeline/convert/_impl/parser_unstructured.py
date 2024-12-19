import re

import click
from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.pptx import partition_pptx
from unstructured.partition.xlsx import partition_xlsx

from leettools.common.logging import logger
from leettools.context_manager import Context, ContextManager
from leettools.eds.pipeline.convert._impl import converter_utils
from leettools.settings import SystemSettings

from ..parser import AbstractParser

NUM_HEADING_PATTERN = r"^(\d+(\.\d+)*)\s+(.*)"
IGNORE_LIST = ["Page ", "Copyright "]
ALLOWED_TYPES = ["Title", "NarrativeText", "Table"]


class ParserUnstructured(AbstractParser):
    """Class to parse PDF content and convert it to Markdown."""

    def __init__(self, settings: SystemSettings):
        """
        Initializes the UnstructuredPDFParser class.
        """
        super().__init__()
        self.settings = settings

    def _replacement(self, match: re.Match) -> str:
        """
        Replaces the match with the appropriate markdown prefix.

        Args:
            match: The match to be replaced.

        Returns:
            The match with the appropriate markdown prefix.
        """
        level = (
            match.group(1).count(".") + 1
        )  # Count the dots to determine the heading level
        return "#" * level

    def docx2md(self, docx_filepath: str) -> str:
        """
        Parses the DOCX and returns the content in markdown format.

        Args:
            docx_filepath: The path to the DOCX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting DOCX to markdown: {docx_filepath}")
        rtn_text = ""
        try:
            elements = partition_docx(filename=docx_filepath)
            return "\n\n".join([str(el) for el in elements])
        except Exception as exc:
            logger().error(f"Failed to parser {docx_filepath}, error: {exc}")
            return rtn_text

    def pdf2md(self, pdf_filepath: str) -> str:
        """
        Parses the PDF and returns the content in markdown format.

        Args:
            pdf_filepath: The path to the PDF file.

        Returns:
            The content in markdown format.
        """
        rtn_text = ""
        elements = partition_pdf(
            filename=pdf_filepath, strategy="hi_res", check_extractable=False
        )
        for el in elements:
            el_dict = el.to_dict()
            el_type = el_dict["type"]
            el_text = el_dict["text"]
            if el_type not in ALLOWED_TYPES:
                continue

            if el_type == "Table":
                rtn_text += converter_utils.parse_table(self.settings, el_text) + "\n\n"
                continue
            if any(el_text.startswith(ignore) for ignore in IGNORE_LIST):
                continue
            else:
                match = re.match(NUM_HEADING_PATTERN, el_text)
                if match:
                    markdown_prefix = self._replacement(match)
                    rtn_text += f"\n\n{markdown_prefix} {el_text}\n\n"
                else:
                    rtn_text += el_text + "\n\n"
        header_text = rtn_text[:200]
        title = converter_utils.extract_title(self.settings, header_text)
        return f"{title}\n\n{rtn_text}"

    def pptx2md(self, pptx_filepath: str) -> str:
        """
        Parses the PPTX and returns the content in markdown format.

        Args:
            pptx_filepath: The path to the PPTX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting PPTX to markdown: {pptx_filepath}")
        rtn_text = ""
        try:
            elements = partition_pptx(filename=pptx_filepath)
            return "\n\n".join([str(el) for el in elements])
        except Exception as exc:
            logger().error(f"Failed to parser {pptx_filepath}, error: {exc}")
            return rtn_text

    def xlsx2md(self, xlsx_filepath: str) -> str:
        """
        Parses the XLSX and returns the content in markdown format.

        Args:
            xlsx_filepath: The path to the XLSX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting XLSX to markdown: {xlsx_filepath}")
        rtn_text = ""
        try:
            elements = partition_xlsx(filename=xlsx_filepath)
            for table in elements:
                rtn_text += table.text + "\n\n"
            return rtn_text
        except Exception as exc:
            logger().error(f"Failed to parser {xlsx_filepath}, error: {exc}")
            return rtn_text


@click.command()
@click.option(
    "-i",
    "--input_file",
    "input_file",
    required=True,
    help="The input pdf file.",
)
@click.option(
    "-o",
    "--output_file",
    "output_file",
    required=True,
    help="The output markdown file.",
)
def pdf_to_md(input_file: str, output_file: str) -> None:
    context = ContextManager().get_context()  # type: Context
    pdf_parser = ParserUnstructured(context.settings)
    rtn_text = pdf_parser.pdf2md(input_file)
    with open(output_file, "w", encoding="utf8") as f:
        f.write(rtn_text)


if __name__ == "__main__":
    pdf_to_md()
