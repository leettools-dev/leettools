import os
import traceback
from pathlib import Path
from typing import List, Optional

from leettools.common.logging import logger
from leettools.core.consts.return_code import ReturnCode
from leettools.core.repo.document_store import AbstractDocumentStore
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.document import DocumentCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.pipeline.convert._impl.parser_html import ParserHTML
from leettools.eds.pipeline.convert.converter import AbstractConverter
from leettools.eds.pipeline.convert.parser import create_parser
from leettools.settings import (
    DOCX_EXT,
    HTML_EXT,
    MD_EXT,
    PDF_EXT,
    PPTX_EXT,
    TXT_EXT,
    XLS_EXT,
    XLSX_EXT,
    SystemSettings,
    is_media_file,
)

PARSE_ACTION = "parse"
LOAD_ACTION = "load"


class ConverterLocal(AbstractConverter):
    """Class to parse and load website content to the docstore."""

    docsink_list: Optional[List[DocSink]] = None
    docstore: AbstractDocumentStore = None
    action: str = PARSE_ACTION

    def __init__(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsink: DocSink,
        docstore: AbstractDocumentStore,
        settings: SystemSettings,
    ):
        """
        Initializes the WebsiteParser class.

        Args:
            input_folder: The input folder to parse and load.
            source: The root url of the website.
            action: The action: parse or load.
        """
        self.org = org
        self.kb = kb
        self.docsink = docsink
        self.docstore = docstore
        self.local_folder = os.path.join(
            settings.DOCUMENT_LOCAL_DIR,
            org.org_id,
            kb.kb_id,
            docsink.docsink_uuid,
        )
        self.settings = settings
        self.log_location: str = None
        if not os.path.exists(self.local_folder):
            os.makedirs(self.local_folder)

    def _get_target_file_path(self) -> str:
        # original_filepath = uri_to_path(self.docsink.raw_doc_uri)
        original_filepath = Path(self.docsink.raw_doc_uri)
        filename = os.path.basename(original_filepath)
        if not filename.endswith(MD_EXT):
            filename = f"{filename}{MD_EXT}"
        return os.path.join(self.local_folder, filename)

    def _load_file(self) -> ReturnCode:
        """
        Add the markdown content to the metadata document store.
        """
        file_path = Path(self.docsink.raw_doc_uri)
        if is_media_file(file_path.suffix):
            document_create = DocumentCreate(
                docsink=self.docsink,
                content="media data content placeholder",
                doc_uri=self.docsink.raw_doc_uri,
            )
        else:
            md_file_path = self._get_target_file_path()

            if Path(md_file_path).exists() is False:
                logger().error(f"markdown file {md_file_path} does not exist!")
                return ReturnCode.FAILURE

            logger().debug(f"Adding {md_file_path} to document store...")
            # add md_content to the metadata docstore
            with open(md_file_path, "r", encoding="utf-8") as md_file:
                md_content = md_file.read()

            document_create = DocumentCreate(
                docsink=self.docsink,
                content=md_content,
                doc_uri=md_file_path,
            )
        document = self.docstore.create_document(
            org=self.org, kb=self.kb, document_create=document_create
        )
        if document is None:
            logger().error(
                f"Adding {self.docsink.raw_doc_uri} to document store failed!"
            )
            return ReturnCode.FAILURE
        else:
            logger().debug(
                f"Adding {self.docsink.raw_doc_uri} to document store succeeded!"
            )
            return ReturnCode.SUCCESS

    def _parse_file(self) -> ReturnCode:
        """
        Parse the document and save it as a markdown file.
        """

        # file_path = uri_to_path(self.docsink.raw_doc_uri)
        logger().debug(f"docsink raw_doc_uri: {self.docsink.raw_doc_uri}")
        file_path = Path(self.docsink.raw_doc_uri)
        logger().debug(f"file_path: {file_path}")
        logger().debug(f"file_path.suffix: {file_path.suffix}")
        if is_media_file(file_path.suffix):
            logger().debug(f"Skip media file {file_path} for parsing.")
            return ReturnCode.SUCCESS

        output_file_path = self._get_target_file_path()
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        output_file_created = False

        if Path(file_path).exists() is False:
            logger().error(f"File {file_path} does not exist!")
            return ReturnCode.FAILURE

        logger().debug(f"Converting {file_path} to {output_file_path}")
        if file_path.suffix == HTML_EXT:
            # TODO: this seems to have some problems, need to investigate
            html_parser = ParserHTML()
            md_content = html_parser.html2md(file_path)
        elif (
            file_path.suffix == PDF_EXT
            or file_path.suffix == DOCX_EXT
            or file_path.suffix == PPTX_EXT
            or file_path.suffix == XLSX_EXT
            or file_path.suffix == XLS_EXT
        ):
            parser_module = self.settings.DEFAULT_PARSER
            logger().debug(f"Using parser: {parser_module}")
            parser = create_parser(self.settings, parser_module)
            md_content = parser.file2md(str(file_path), output_file_path)
            output_file_created = True
        elif file_path.suffix == MD_EXT:
            with open(file_path, "r", encoding="utf-8") as md_file:
                md_content = md_file.read()
        elif file_path.suffix == TXT_EXT:
            with open(file_path, "r", encoding="utf-8") as txt_file:
                md_content = txt_file.read()
        elif is_media_file(file_path.suffix):
            logger().debug(f"Skip media file {file_path} for parsing.")
            return ReturnCode.SUCCESS
        else:
            logger().error(f"Unsupported file type for parsing: {str(file_path)}")
            return ReturnCode.FAILURE

        if md_content == "":
            logger().warning(f"Markdown content is empty for {file_path}!")
            return ReturnCode.FAILURE

        # some parser may already created the output file
        if not output_file_created:
            logger().debug(f"Writing {output_file_path}...")
            with open(output_file_path, "w", encoding="utf-8") as md_file:
                md_file.write(md_content)
        else:
            # check if the output file exists
            if not Path(output_file_path).exists():
                logger().warning(f"Output file does not exist: {output_file_path}!")
                return ReturnCode.FAILURE
        return ReturnCode.SUCCESS

    def set_log_location(self, log_location: str) -> None:
        self.log_location = log_location

    def convert(self) -> ReturnCode:
        """
        Convert a list of document sinks to a list of documents
        and save them to the docstore.

        Args:
        doc_sink: The docsink to convert.

        Returns:
        The return code.
        """
        rtn_code = ReturnCode.SUCCESS

        self.action = PARSE_ACTION
        if self.log_location:
            log_handler = logger().log_to_file(self.log_location)
        else:
            log_handler = None
        try:
            rtn_code = self._parse_file()
            if rtn_code == ReturnCode.SUCCESS:
                self.action = LOAD_ACTION
                rtn_code = self._load_file()
                if rtn_code == ReturnCode.FAILURE:
                    return rtn_code
            else:
                return rtn_code
            return rtn_code
        except Exception as e:
            trace = traceback.format_exc()
            logger().error(f"Error converting document: {trace}")
            return ReturnCode.FAILURE
        finally:
            if log_handler:
                logger().remove_file_handler()
