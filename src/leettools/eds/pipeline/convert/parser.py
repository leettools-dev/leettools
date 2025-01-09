import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from leettools.common.exceptions import UnexpectedCaseException
from leettools.settings import (
    DOCX_EXT,
    PDF_EXT,
    PPTX_EXT,
    XLS_EXT,
    XLSX_EXT,
    SystemSettings,
)


class AbstractParser(ABC):
    @abstractmethod
    def pdf2md(self, pdf_path: str, target_path: Optional[Path] = None) -> str:
        """
        Parse a PDF file and return the text.

        Args:
        - pdf_path: Path to the PDF file.
        - target_path: File path to save the parsed text. If None, the text is not saved.

        Returns:
        - The parsed text.
        """
        pass

    @abstractmethod
    def docx2md(self, docx_path: str, target_path: Optional[Path] = None) -> str:
        """
        Parse a DOCX file and return the text.

        Args:
        - docx_path: Path to the DOCX file.
        - target_path: File path to save the parsed text. If None, the text is not saved.

        Returns:
        - The parsed text.
        """
        pass

    @abstractmethod
    def pptx2md(self, pptx_path: str, target_path: Optional[Path] = None) -> str:
        """
        Parse a PPTX file and return the text.

        Args:
        - pptx_path: Path to the PPTX file.
        - target_path: File path to save the parsed text. If None, the text is not saved.

        Returns:
        - The parsed text.
        """
        pass

    @abstractmethod
    def xlsx2md(self, xlsx_path: str, target_path: Optional[Path] = None) -> str:
        """
        Parse an XLSX file and return the text.

        Args:
        - xlsx_path: Path to the XLSX file.
        - target_path: File path to save the parsed text. If None, the text is not saved.

        Returns:
        - The parsed text.
        """
        pass

    def file2md(self, file_path: str, target_path: Optional[Path] = None) -> str:
        """
        Parse a file and return the text.

        Args:
        - file_path: Path to the file.
        - target_path: File path to save the parsed text. If None, the text is not saved.

        Returns:
        - The parsed text.
        """
        # Get the file extension with the dot
        file_ext = os.path.splitext(file_path)[1]
        if file_ext == PDF_EXT:
            return self.pdf2md(file_path, target_path)
        elif file_ext == DOCX_EXT:
            return self.docx2md(file_path, target_path)
        elif file_ext == PPTX_EXT:
            return self.pptx2md(file_path, target_path)
        elif file_ext == XLSX_EXT or file_ext == XLS_EXT:
            return self.xlsx2md(file_path, target_path)
        else:
            raise UnexpectedCaseException(
                f"Unsupported file type for parsing: {file_path}"
            )


def create_parser(settings: SystemSettings, parser_module: str) -> AbstractParser:
    """
    Create a parser instance based on the specified type.

    Args:
    - settings: System settings for configuration
    - parser_module: module name of parser to create

    Returns:
    - An instance of AbstractParser
    """
    from leettools.common.utils import factory_util

    if "." not in parser_module:
        module_name = f"{__package__}._impl.{parser_module}"
    else:
        module_name = parser_module

    return factory_util.create_object(
        module_name,
        AbstractParser,
        settings=settings,
    )
