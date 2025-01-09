from pathlib import Path
from typing import Optional

import requests

from leettools.common.logging import logger
from leettools.eds.pipeline.convert.parser import AbstractParser
from leettools.settings import SystemSettings


class ParserEDS(AbstractParser):
    """Class to parse a file and convert it to Markdown."""

    def __init__(self, settings: SystemSettings):
        self.api_uri = settings.CONVERTER_API_URL

    def _call_eds_service_api(
        self, filepath: str, target_path: Optional[Path] = None
    ) -> str:
        rtn_text = ""
        headers = {"accept": "application/json"}
        files = {"file": (filepath, open(filepath, "rb"))}

        try:
            response = requests.post(self.api_uri, headers=headers, files=files)
            rtn_text = response.text
            if target_path:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(rtn_text)
            return rtn_text
        except requests.exceptions.HTTPError as e:
            logger().error(f"HTTP error occurred: {e}")
        except Exception as e:
            logger().error(f"An error occurred: {e}")
        finally:
            files["file"][1].close()  # Close the file after the request

    def docx2md(self, docx_filepath: str, target_path: Optional[Path] = None) -> str:
        logger().debug(f"Converting DOCX to markdown: {docx_filepath}")
        return self._call_eds_service_api(docx_filepath, target_path)

    def pdf2md(self, pdf_filepath: str, target_path: Optional[Path] = None) -> str:
        logger().debug(f"Converting PDF to markdown: {pdf_filepath}")
        return self._call_eds_service_api(pdf_filepath, target_path)

    def pptx2md(self, pptx_filepath: str, target_path: Optional[Path] = None) -> str:
        logger().debug(f"Converting PPTX to markdown: {pptx_filepath}")
        return self._call_eds_service_api(pptx_filepath, target_path)

    def xlsx2md(self, xlsx_filepath: str, target_path: Optional[Path] = None) -> str:
        logger().debug(f"Converting XLSX to markdown: {xlsx_filepath}")
        return self._call_eds_service_api(xlsx_filepath, target_path)
