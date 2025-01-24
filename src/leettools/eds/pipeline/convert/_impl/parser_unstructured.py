import re
from pathlib import Path
from typing import Optional

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

    def docx2md(self, docx_filepath: str, target_path: Optional[Path] = None) -> str:

        logger().debug(f"Converting DOCX to markdown: {docx_filepath}")
        try:
            elements = partition_docx(filename=docx_filepath)
            md_text = "\n\n".join([str(el) for el in elements])
            if target_path:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(md_text)
        except Exception as exc:
            logger().error(f"Failed to parser {docx_filepath}, error: {exc}")
            return ""

    def pdf2md(self, pdf_filepath: str, target_path: Optional[Path] = None) -> str:

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
        return_text = f"{title}\n\n{rtn_text}"
        if target_path:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(return_text)
        return return_text

    def pptx2md(self, pptx_filepath: str, target_path: Optional[Path] = None) -> str:

        logger().debug(f"Converting PPTX to markdown: {pptx_filepath}")
        try:
            elements = partition_pptx(filename=pptx_filepath)
            return_text = "\n\n".join([str(el) for el in elements])
            if target_path:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(return_text)
            return return_text
        except Exception as exc:
            logger().error(f"Failed to parser {pptx_filepath}, error: {exc}")
            return ""

    def xlsx2md(self, xlsx_filepath: str, target_path: Optional[Path] = None) -> str:

        logger().debug(f"Converting XLSX to markdown: {xlsx_filepath}")
        rtn_text = ""
        try:
            elements = partition_xlsx(filename=xlsx_filepath)
            for table in elements:
                rtn_text += table.text + "\n\n"
            if target_path:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(rtn_text)
            return rtn_text
        except Exception as exc:
            logger().error(f"Failed to parser {xlsx_filepath}, error: {exc}")
            return ""
