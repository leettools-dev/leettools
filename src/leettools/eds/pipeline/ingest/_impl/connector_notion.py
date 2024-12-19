import json
import os
import traceback
from typing import List, Optional, Tuple

import requests
from notion_client import Client

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.consts.return_code import ReturnCode
from leettools.core.repo.docsink_store import AbstractDocsinkStore
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.pipeline.ingest._impl.notion.schemas.block import PDF_TYPE, Block
from leettools.eds.pipeline.ingest.connector import AbstractConnector


class ConnectorNotion(AbstractConnector):
    def __init__(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        docsinkstore: AbstractDocsinkStore,
        display_logger: Optional[EventLogger] = None,
    ):
        self.context = context
        self.org = org
        self.kb = kb
        self.kb_id = docsource.kb_id  # we can remove the kb_id in docsource later

        self.docsinkstore = docsinkstore

        if docsource.ingest_config is None:
            raise exceptions.ConfigValueException(
                "ingest_config", "Missing ingest_config in docsource"
            )
        access_token = docsource.ingest_config.extra_parameters.get("access_token")
        if access_token is None:
            raise exceptions.ConfigValueException(
                "access_token", "Missing access_token in ingest_config"
            )

        self.notion = Client(auth=access_token)
        self.doc_uri = docsource.uri
        self.docsource_uuid = docsource.docsource_uuid
        self.docsink_root_uri = f"{context.settings.DATA_ROOT}/notion"
        self.file_list = []
        self.log_location = None
        self.docsink_list = []
        if display_logger is not None:
            self.display_logger = display_logger
        else:
            self.display_logger = logger()

    def _download_external_file(self, file_uri: str) -> ReturnCode:
        try:
            response = requests.get(file_uri, timeout=100)
            response.raise_for_status()  # Raise an error on bad status
        except requests.RequestException as e:
            trace = traceback.format_exc()
            self.display_logger.error(f"Failed to retrieve {file_uri}: {trace}")
            return ReturnCode.FAILURE

        extract_file_name = file_uri.split("?")[0]
        file_name = os.path.basename(extract_file_name)
        file_path = f"{self.docsink_root_uri}/{file_name}"
        self.display_logger.info(f"Downloading {file_name} to {file_path}")
        with open(file_path, "wb") as f:
            f.write(response.content)
        docsink_create = DocSinkCreate(
            docsource_uuid=self.docsource_uuid,
            kb_id=self.kb_id,
            original_doc_uri=file_uri,
            raw_doc_uri=file_path,
        )
        docsink = self.docsinkstore.create_docsink(self.org, self.kb, docsink_create)
        if docsink is not None:
            self.docsink_list.append(docsink)
            return ReturnCode.SUCCESS
        else:
            return ReturnCode.FAILURE

    def _get_block_instance(self, block_id: str) -> Block:
        block = self.notion.blocks.retrieve(block_id=block_id)
        block_instance = Block.from_dict(block)
        if block["has_children"] is True:
            response = self.notion.blocks.children.list(block_id=block_id)
            for child_block in response["results"]:
                child_instance = self._get_block_instance(child_block["id"])
                block_instance.children.append(child_instance)
        return block_instance

    def _parse_block(
        self, block: Block, file_list: List[str] = []
    ) -> Tuple[str, List[str]]:
        block_object_text = block.block_object_to_text(self.notion)
        if block.type == PDF_TYPE:
            file_list.append(block.block_object.file.url)
        if block.children is not None and len(block.children) > 0:
            for child in block.children:
                (child_object_text, file_list) = self._parse_block(child, file_list)
                block_object_text += f"{child_object_text}\n"
        return (block_object_text, file_list)

    def _ingest(self) -> ReturnCode:
        if "?v=" in self.doc_uri:
            # it is a database page
            root_block_id = self.doc_uri.split("?v=")[0].split("/")[-1]
        else:
            # it is a normal page
            root_block_id = self.doc_uri.split("-")[-1]
        self.docsink_root_uri = f"{self.docsink_root_uri}/{root_block_id}"
        rtn_instance = self._get_block_instance(root_block_id)

        os.makedirs(self.docsink_root_uri, exist_ok=True)

        instance_dump = rtn_instance.to_dict()
        output = f"{self.docsink_root_uri}/instance.json"
        with open(output, "w", encoding="utf8") as f:
            f.write(json.dumps(instance_dump, indent=4))

        (md_text, file_list) = self._parse_block(rtn_instance)

        self.display_logger.info(f"Saving main content data to {self.docsink_root_uri}")
        md_path = f"{self.docsink_root_uri}/content.md"
        with open(md_path, "w") as f:
            f.write(md_text)
        docsink_create = DocSinkCreate(
            docsource_uuid=self.docsource_uuid,
            kb_id=self.kb_id,
            original_doc_uri=self.doc_uri,
            raw_doc_uri=md_path,
        )
        docsink = self.docsinkstore.create_docsink(self.org, self.kb, docsink_create)
        if docsink is None:
            return ReturnCode.FAILURE
        self.docsink_list.append(docsink)

        for file_uri in file_list:
            rtncode = self._download_external_file(file_uri)
            if rtncode != ReturnCode.SUCCESS:
                return rtncode
        return ReturnCode.SUCCESS

    def get_ingested_docsink_list(self) -> Optional[List[DocSinkCreate]]:
        return self.docsink_list

    def ingest(self) -> ReturnCode:
        if self.log_location:
            log_handler = self.display_logger.log_to_file(self.log_location)
        else:
            log_handler = None
        try:
            rtn_code = self._ingest()
            return rtn_code
        except Exception as e:
            trace = traceback.format_exc()
            self.display_logger.error(f"Error ingesting notion document: {trace}")
            return ReturnCode.FAILURE
        finally:
            if log_handler:
                self.display_logger.remove_file_handler()

    def set_log_location(self, log_location: str) -> None:
        self.log_location = log_location
