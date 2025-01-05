import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import leettools.common.utils.url_utils
from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import get_logger, logger
from leettools.common.utils import file_utils, time_utils
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.metadata._impl.duckdb.kb_metadata_duckdb_schema import (
    DuckDBKBMetadataSchema,
)
from leettools.eds.metadata.kb_metadata_manager import AbstractKBMetadataManager
from leettools.eds.metadata.schemas.kb_metadata import KBMetadata


class KBMetadataManagerDuckDB(AbstractKBMetadataManager):
    """
    The Metadata for Knowledge Bases such as top domains, keywords, links, and authors.
    """

    def __init__(self, context: Context):

        self.logger = get_logger(name="scheduler")

        self.settings = context.settings

        self.repo_manager = context.get_repo_manager()
        self.task_manager = context.get_task_manager()
        self.taskstore = self.task_manager.get_taskstore()
        self.jobstore = self.task_manager.get_jobstore()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.docsource_store = self.repo_manager.get_docsource_store()
        self.docsink_store = self.repo_manager.get_docsink_store()
        self.document_store = self.repo_manager.get_document_store()
        self.segment_store = self.repo_manager.get_segment_store()

        self.duckdb_client = DuckDBClient(self.settings)

    def _dict_to_kb_metadata(self, kb_metadata_dict: Dict[str, Any]) -> KBMetadata:
        for attr in [
            KBMetadata.FIELD_NUMBER_OF_DOCSINKS,
            KBMetadata.FIELD_NUMBER_OF_DOCSOURCES,
            KBMetadata.FIELD_NUMBER_OF_DOCUMENTS,
            KBMetadata.FIELD_RAW_DATA_SIZE,
            KBMetadata.FIELD_PROCESSED_DATA_SIZE,
            KBMetadata.FIELD_TOP_DOMAINS,
            KBMetadata.FIELD_TOP_KEYWORDS,
            KBMetadata.FIELD_TOP_LINKS,
            KBMetadata.FIELD_TOP_AUTHORS,
        ]:
            if attr in kb_metadata_dict:
                kb_metadata_dict[attr] = json.loads(kb_metadata_dict[attr])
        return KBMetadata.model_validate(kb_metadata_dict)

    def _get_table_name(self, org: Org) -> str:
        org_db_name = Org.get_org_db_name(org.org_id)
        return self.duckdb_client.create_table_if_not_exists(
            org_db_name,
            self.settings.COLLECTION_KB_METADATA,
            DuckDBKBMetadataSchema.get_schema(),
        )

    def _kb_metadata_to_dict(self, kb_metadata: KBMetadata) -> Dict[str, Any]:
        kb_metadata_dict = kb_metadata.model_dump()
        for attr in [
            KBMetadata.FIELD_NUMBER_OF_DOCSINKS,
            KBMetadata.FIELD_NUMBER_OF_DOCSOURCES,
            KBMetadata.FIELD_NUMBER_OF_DOCUMENTS,
            KBMetadata.FIELD_RAW_DATA_SIZE,
            KBMetadata.FIELD_PROCESSED_DATA_SIZE,
            KBMetadata.FIELD_TOP_DOMAINS,
            KBMetadata.FIELD_TOP_KEYWORDS,
            KBMetadata.FIELD_TOP_LINKS,
            KBMetadata.FIELD_TOP_AUTHORS,
        ]:
            if attr in kb_metadata_dict:
                kb_metadata_dict[attr] = json.dumps(kb_metadata_dict[attr])
        return kb_metadata_dict

    def _save_kb_metadata(self, org: Org, kb_metadata: KBMetadata) -> None:
        table_name = self._get_table_name(org)
        kb_metadata_dict = self._kb_metadata_to_dict(kb_metadata)
        column_list = list(kb_metadata_dict.keys())
        value_list = list(kb_metadata_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )

    def get_kb_metadata(self, org: Org, kb_id: str) -> Optional[KBMetadata]:
        table_name = self._get_table_name(org)
        # find the kb metadata by kb_id and return the one with latest created_at
        where_clause = (
            f"WHERE {KBMetadata.FIELD_KB_ID} = ? "
            f"ORDER BY {KBMetadata.FIELD_CREATED_AT} DESC "
            f"LIMIT 1"
        )
        value_list = [kb_id]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if rtn_dict is None:
            return None
        return self._dict_to_kb_metadata(rtn_dict)

    def process_kb_metadata(self, org: Org, kb: KnowledgeBase) -> KBMetadata:
        kb_metadata = KBMetadata(
            kb_id=kb.kb_id,
            kb_name=kb.name,
            created_at=time_utils.current_datetime(),
            number_of_docsources={src_type: 0 for src_type in DocSourceType},
            number_of_docsinks={src_type: 0 for src_type in DocSourceType},
            number_of_documents={src_type: 0 for src_type in DocSourceType},
            raw_data_size={src_type: 0 for src_type in DocSourceType},
            processed_data_size={src_type: 0 for src_type in DocSourceType},
            top_domains={},
            top_keywords={},
            top_links={},
            top_authors={},
        )

        docsources = self.docsource_store.get_docsources_for_kb(org, kb)
        for docsource in docsources:
            source_type = docsource.source_type
            kb_metadata.number_of_docsources[source_type] += 1
            for docsink in self.docsink_store.get_docsinks_for_docsource(
                org, kb, docsource
            ):
                kb_metadata.number_of_docsinks[source_type] += 1

                if docsink.size == 0 or docsink.size is None:
                    doc_hash, doc_size = file_utils.file_hash_and_size(
                        docsink.raw_doc_uri
                    )
                    docsink.size = doc_size
                    docsink.raw_doc_hash = doc_hash
                    self.docsink_store.update_docsink(org, kb, docsink)
                    kb_metadata.raw_data_size[source_type] += doc_size
                else:
                    kb_metadata.raw_data_size[source_type] += docsink.size

                doc_list = self.document_store.get_documents_for_docsink(
                    org, kb, docsink
                )
                if len(doc_list) == 0:
                    logger().warning(f"Docsink {docsink.docsink_uuid} has no documents")
                    continue

                if len(doc_list) > 1:
                    logger().warning(
                        f"Docsink {docsink.docsink_uuid} has multiple documents"
                        " - using the first one"
                    )
                document = doc_list[0]
                kb_metadata.number_of_documents[source_type] += 1
                kb_metadata.processed_data_size[source_type] += len(document.content)

                if document.keywords:
                    for keyword in document.keywords:
                        if keyword in kb_metadata.top_keywords:
                            kb_metadata.top_keywords[keyword] += 1
                        else:
                            kb_metadata.top_keywords[keyword] = 1
                if document.links:
                    for link in document.links:
                        if link in kb_metadata.top_links:
                            kb_metadata.top_links[link] += 1
                        else:
                            kb_metadata.top_links[link] = 1
                if document.original_uri.startswith("http"):
                    tld = leettools.common.utils.url_utils.get_first_level_domain_from_url(
                        document.original_uri
                    )
                    if tld in kb_metadata.top_domains:
                        kb_metadata.top_domains[tld] += 1
                    else:
                        kb_metadata.top_domains[tld] = 1
                if document.authors:
                    for author in document.authors:
                        if author in kb_metadata.top_authors:
                            kb_metadata.top_authors[author] += 1
                        else:
                            kb_metadata.top_authors[author] = 1
        self._save_kb_metadata(org, kb_metadata)
        return kb_metadata

    def process_metadata_for_all_kbs(self) -> None:
        start_time = time.perf_counter()
        orgs = self.org_manager.list_orgs()
        for org in orgs:
            kbs = self.kb_manager.get_all_kbs_for_org(org)
            for kb in kbs:
                self.process_kb_metadata(org, kb)
        end_time = time.perf_counter()
        self.logger.info(
            f"Processed metadata for all KBs in {end_time - start_time} seconds"
        )
        return

    def scan_kb_for_metadata(self) -> None:
        orgs = self.org_manager.list_orgs()
        for org in orgs:
            kbs = self.kb_manager.get_all_kbs_for_org(org)
            for kb in kbs:
                kb_metadata = self.get_kb_metadata(org, kb.kb_id)

    def get_docs_from_domain(
        self, org: Org, kb: KnowledgeBase, top_level_domain: str
    ) -> List[Document]:
        matched_docs: List[Document] = []
        documents = self.document_store.get_documents_for_kb(org, kb)
        for doc in documents:
            if doc.original_uri.startswith("http"):
                tld = leettools.common.utils.url_utils.get_first_level_domain_from_url(
                    doc.original_uri
                )
                if tld == top_level_domain:
                    matched_docs.append(doc)
        return matched_docs

    def get_docs_with_keyword(
        self, org: Org, kb: KnowledgeBase, keyword: str
    ) -> List[Document]:
        """
        Retrieves a list of documents with a specific keyword.

        Args:
            org (Org): The organization.
            kb (KnowledgeBase): The knowledge base.
            keyword (str): The keyword to filter the documents.

        Returns:
            List[Document]: A list of documents containing the specified keyword.
        """

        matched_docs: List[Document] = []
        documents = self.document_store.get_documents_for_kb(org, kb)
        for doc in documents:
            if doc.keywords and keyword in doc.keywords:
                matched_docs.append(doc)
        return matched_docs

    def get_docs_from_author(
        self, org: Org, kb: KnowledgeBase, author: str
    ) -> List[Document]:
        """
        Retrieves a list of documents from a specific author.

        Args:
            org (Org): The organization.
            kb (KnowledgeBase): The knowledge base.
            author (str): The author to filter the documents.

        Returns:
            List[Document]: A list of documents from the specified author.
        """

        matched_docs: List[Document] = []
        documents = self.document_store.get_documents_for_kb(org, kb)
        for doc in documents:
            if doc.authors and author in doc.authors:
                matched_docs.append(doc)
        return matched_docs


if __name__ == "__main__":
    context = ContextManager().get_context()
    metadata_manager = KBMetadataManagerDuckDB(context)
    metadata_manager.process_metadata_for_all_kbs()
    metadata_manager.scan_kb_for_metadata()
