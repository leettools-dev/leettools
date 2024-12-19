import json
import os
import re
import traceback
from re import Match

import click
import urllib3
from llmsherpa.readers import (
    Block,
    Document,
    LayoutPDFReader,
    ListItem,
    Paragraph,
    Section,
    Table,
)

from leettools.common.logging import logger
from leettools.context_manager import Context, ContextManager
from leettools.eds.pipeline.convert._impl import converter_utils
from leettools.eds.pipeline.convert.parser import AbstractParser
from leettools.settings import SystemSettings

UPPERCASE_LINE_PATTERN = r"^[A-Z\s]+$"
UPPERCASE_FIRST_PATTERN = r"^([A-Z][a-z]+)(\s[A-Z][a-z]+)*$"

SECTION_HEADING_PATTERN = r"^(?:SECTION\s+)?(\d+(?:\.\d+)*\.?)\s*[:.]?\s*(.*)"
MULTIPLE_HEADINGS_PATTERN = r"(?<=\D)(?=\d+\s+\D)"

# TODO: this list should be managed by users themselves.
NON_HEADINGS_PATTERN_LIST = [r"^\d+kV\s+"]


class ParserLLMSherpa(AbstractParser):
    """Class to parse PDF content and convert it to Markdown."""

    pdf_reader: LayoutPDFReader = None

    def __init__(self, settings: SystemSettings):
        """
        Initializes the LayoutPDFParser class.
        """
        super().__init__()
        self.settings = settings

        self.parser_api_url = os.environ.get(
            "LLMSHERPA_API_URL",
            "https://readers.llmsherpa.com/api/document/"
            "developer/parseDocument?renderFormat=all",
        )
        self.pdf_reader = LayoutPDFReader(self.parser_api_url)
        self.api_connection = urllib3.PoolManager()

    def _convert_section_to_markdown(self, match: Match) -> str:
        segments = match.group(1).split(".")  # Count the dots to determine depth
        new_segments = []
        for segment in segments:
            if segment != "":
                new_segments.append(segment)
        markdown_heading = "#" * max(1, len(new_segments))
        section_title = match.group(2)
        return f"{markdown_heading} {match.group(1)} {section_title}"

    def _convert_line_to_markdown(self, line: str) -> str:
        logger().debug(f"Converting line: {line}")
        match = re.match(SECTION_HEADING_PATTERN, line)
        if match:
            return re.sub(
                SECTION_HEADING_PATTERN,
                self._convert_section_to_markdown,
                line,
                re.IGNORECASE,
            )

        match = re.match(UPPERCASE_LINE_PATTERN, line)
        if match:
            return f"# {line}"

        match = re.match(UPPERCASE_FIRST_PATTERN, line)
        if match:
            return f"# {line}"

        return line

    def _handle_numberic_heading(self, match: Match) -> str:
        segments = match.group(1).split(".")  # Count the dots to determine depth
        new_segments = []
        for segment in segments:
            if segment != "":
                new_segments.append(segment)
        markdown_heading = "#" * max(1, len(new_segments))
        section_title = match.group(2)
        return f"{markdown_heading} {match.group(1)} {section_title}"

    def _handle_headings(self, line: str) -> str:
        logger().debug(f"Converting line: {line}")

        for non_heading_pattern in NON_HEADINGS_PATTERN_LIST:
            if re.match(non_heading_pattern, line):
                return line

        match = re.match(SECTION_HEADING_PATTERN, line)
        if match:
            return re.sub(
                SECTION_HEADING_PATTERN,
                self._handle_numberic_heading,
                line,
                re.IGNORECASE,
            )

        match = re.match(UPPERCASE_LINE_PATTERN, line)
        if match:
            return f"# {line}"

        match = re.match(UPPERCASE_FIRST_PATTERN, line)
        if match:
            return f"# {line}"

        return line

    def _traversal_doc(self, node: Block) -> str:
        """
        Traverses the document and returns the markdown content.

        Args:
            node: The node to be traversed.

        Returns:
            The markdown content.
        """
        md_text = ""
        node_type = ""
        logger().set_level("INFO")
        if isinstance(node, Section):
            node_type = "Section"
            rtn_node_text = self._handle_headings(node.to_text())
            md_text += rtn_node_text + "\n\n"
            logger().debug(rtn_node_text)
        elif isinstance(node, Table):
            node_type = "Table"
            table_content = converter_utils.parse_table(self.settings, node.to_text())
            md_text += table_content + "\n\n"
            logger().debug(table_content)
        elif isinstance(node, Paragraph):
            node_type = "Paragraph"
            line = self._handle_headings(node.to_text())
            md_text += line + "\n\n"
            logger().debug(line)
        elif isinstance(node, ListItem):
            node_type = "ListItem"
            match = re.match(SECTION_HEADING_PATTERN, node.to_text())
            if match:
                rtn_node_text = self._handle_headings(node.to_text())
                md_text += rtn_node_text + "\n\n"
                logger().debug(rtn_node_text)
            else:
                md_text += node.to_html() + "\n\n"
                logger().debug(node.to_html())
        elif isinstance(node, Block):
            node_type = "Block"
        else:
            raise ValueError(f"Unknown node type: {type(node)}")
        logger().debug(f"\n*{node_type}")
        logger().debug("--------------------------")

        if node_type not in ["ListItem", "Paragraph", "Table"]:
            for child in node.children:
                md_text += self._traversal_doc(child)
        return md_text

    def pdf2md(self, pdf_filepath: str) -> str:
        """
        Parses the PDF file and returns the meaningful
        text content in Markdown format.

        Args:
            pdf_filepath: The path to the PDF file to be parsed.

        Returns:
            The meaningful text content in Markdown format.
        """
        try:
            doc = self.pdf_reader.read_pdf(pdf_filepath)
        except Exception as e:
            trace = traceback.format_exc()
            logger().error(f"Failed to parsePDF file {pdf_filepath}, error: {trace}")
            return ""
        md_text = self._traversal_doc(doc.root_node)
        header_test = md_text[:200]
        title = converter_utils.extract_title(self.settings, header_test)
        return f"{title}\n\n{md_text}"

    def docx2md(self, docx_filepath: str) -> str:
        try:
            with open(docx_filepath, "rb") as f:
                file_data = f.read()
                files = (docx_filepath, file_data, "application/docx")
                parser_response = self.api_connection.request(
                    "POST", self.parser_api_url, fields={"file": files}
                )
                response_json = json.loads(parser_response.data.decode("utf-8"))
                blocks = response_json["return_dict"]["result"]["blocks"]
                return self._traversal_doc(Document(blocks).root_node)
        except Exception as e:
            trace = traceback.format_exc()
            logger().error(f"Failed to parse file {docx_filepath}, error: {trace}")
            return ""

    def pptx2md(self, pptx_path: str) -> str:
        try:
            with open(pptx_path, "rb") as f:
                file_data = f.read()
                files = (pptx_path, file_data, "application/pptx")
                parser_response = self.api_connection.request(
                    "POST", self.parser_api_url, fields={"file": files}
                )
                response_json = json.loads(parser_response.data.decode("utf-8"))
                blocks = response_json["return_dict"]["result"]["blocks"]
                return self._traversal_doc(Document(blocks).root_node)
        except Exception as e:
            trace = traceback.format_exc()
            logger().error(f"Failed to parse file {pptx_path}, error: {trace}")
            return ""

    def xlsx2md(self, xlsx_path: str) -> str:
        try:
            with open(xlsx_path, "rb") as f:
                file_data = f.read()
                files = (xlsx_path, file_data, "application/xlsx")
                parser_response = self.api_connection.request(
                    "POST", self.parser_api_url, fields={"file": files}
                )
                response_json = json.loads(parser_response.data.decode("utf-8"))
                blocks = response_json["return_dict"]["result"]["blocks"]
                return self._traversal_doc(Document(blocks).root_node)
        except Exception as e:
            trace = traceback.format_exc()
            logger().error(f"Failed to parse file {xlsx_path}, error: {trace}")
            return ""


@click.command()
@click.option(
    "-i",
    "--input_file",
    "input_file",
    required=True,
    help="The input file.",
)
@click.option(
    "-o",
    "--output_file",
    "output_file",
    required=True,
    help="The output text file.",
)
def llmsherpa_pdf2md(input_file, output_file):
    context = ContextManager().get_context()  # type: Context
    parser = ParserLLMSherpa(context.settings)
    md_content = parser.file2md(input_file)
    with open(output_file, "w", encoding="utf8") as f:
        f.write(md_content)


if __name__ == "__main__":
    llmsherpa_pdf2md()
