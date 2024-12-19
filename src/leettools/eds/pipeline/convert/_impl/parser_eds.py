import requests

from leettools.common.logging import logger
from leettools.eds.pipeline.convert.parser import AbstractParser
from leettools.settings import SystemSettings


class ParserEDS(AbstractParser):
    """Class to parse a file and convert it to Markdown."""

    def __init__(self, settings: SystemSettings):
        self.api_uri = settings.CONVERTER_API_URL

    def _call_eds_service_api(self, filepath: str) -> str:
        rtn_text = ""
        headers = {"accept": "application/json"}
        files = {"file": (filepath, open(filepath, "rb"))}

        try:
            response = requests.post(self.api_uri, headers=headers, files=files)
            rtn_text = response.text
        except requests.exceptions.HTTPError as e:
            logger().error(f"HTTP error occurred: {e}")
        except Exception as e:
            logger().error(f"An error occurred: {e}")
        finally:
            files["file"][1].close()  # Close the file after the request
            return rtn_text

    def docx2md(self, docx_filepath: str) -> str:
        """
        Parses the DOCX and returns the content in markdown format.

        Args:
            docx_filepath: The path to the DOCX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting DOCX to markdown: {docx_filepath}")
        return self._call_eds_service_api(docx_filepath)

    def pdf2md(self, pdf_filepath: str) -> str:
        """
        Parses the PDF and returns the content in markdown format.

        Args:
            pdf_filepath: The path to the PDF file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting PDF to markdown: {pdf_filepath}")
        return self._call_eds_service_api(pdf_filepath)

    def pptx2md(self, pptx_filepath: str) -> str:
        """
        Parses the PPTX and returns the content in markdown format.

        Args:
            pptx_filepath: The path to the PPTX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting PPTX to markdown: {pptx_filepath}")
        return self._call_eds_service_api(pptx_filepath)

    def xlsx2md(self, xlsx_filepath: str) -> str:
        """
        Parses the XLSX and returns the content in markdown format.

        Args:
            xlsx_filepath: The path to the XLSX file.

        Returns:
            The content in markdown format.
        """
        logger().debug(f"Converting XLSX to markdown: {xlsx_filepath}")
        return self._call_eds_service_api(xlsx_filepath)
