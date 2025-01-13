import json
import uuid
from typing import List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.consts.segment_embedder_type import SegmentEmbedderType
from leettools.core.repo._impl.duckdb.document_store_duckdb_schema import (
    DocumentDuckDBSchema,
)
from leettools.core.repo.document_store import AbstractDocumentStore
from leettools.core.repo.vector_store import (
    create_vector_store_dense,
    create_vector_store_sparse,
)
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import (
    Document,
    DocumentCreate,
    DocumentInDB,
    DocumentUpdate,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings

DOCUMENT_COLLECTION_SUFFIX = "_documents"


class DocumentStoreDuckDB(AbstractDocumentStore):
    """DocumentStore implementation using DuckDB as the backend."""

    def __init__(self, settings: SystemSettings, is_test: bool = False) -> None:
        """Initialize DuckDB connection."""
        self.settings = settings
        self.is_test = is_test
        self.duckdb_client = DuckDBClient(self.settings)

    def _clean_up_related_data(self, org: Org, kb: KnowledgeBase, document: Document):
        """Clean up related data for a document."""
        # Clean up related data
        from leettools.context_manager import ContextManager

        context = ContextManager().get_context()

        # Delete segments and related data
        segment_store = context.get_repo_manager().get_segment_store()
        graph_store = context.get_repo_manager().get_docgraph_store()
        dense_vectorstore = create_vector_store_dense(context)

        if kb.embedder_type == SegmentEmbedderType.HYBRID:
            sparse_vectorstore = create_vector_store_sparse(context)
        else:
            sparse_vectorstore = None

        for segment in segment_store.get_all_segments_for_document(
            org, kb, document.document_uuid
        ):
            segment_store.delete_segment(org, kb, segment)
            # todo: check if we need to delete the relationship
            # graph_store.delete_segments_relationship()
            graph_store.delete_segment_node(segment)
            dense_vectorstore.delete_segment_vectors_by_document_id(
                org, kb, document.document_uuid
            )
            if sparse_vectorstore:
                sparse_vectorstore.delete_segment_vectors_by_document_id(
                    org, kb, document.document_uuid
                )

        # Delete related tasks
        task_store = context.get_task_manager().get_taskstore()
        for task in task_store.get_tasks_for_document(document.document_uuid):
            task_store.delete_task(task.task_uuid)
        for task in task_store.get_tasks_for_docsink(document.docsink_uuid):
            task_store.delete_task(task.task_uuid)

    # Private helper methods
    def _dict_to_document(self, data: dict) -> Document:
        """Convert stored dictionary to Document."""
        if data.get(Document.FIELD_DOCSOURCE_UUIDS):
            uuids = data[Document.FIELD_DOCSOURCE_UUIDS]
            data[Document.FIELD_DOCSOURCE_UUIDS] = uuids.split(",")
        if data.get(Document.FIELD_AUTO_SUMMARY):
            data[Document.FIELD_AUTO_SUMMARY] = json.loads(
                data[Document.FIELD_AUTO_SUMMARY]
            )
        if data.get(Document.FIELD_MANUAL_SUMMARY):
            data[Document.FIELD_MANUAL_SUMMARY] = json.loads(
                data[Document.FIELD_MANUAL_SUMMARY]
            )
        return Document.from_document_in_db(DocumentInDB.model_validate(data))

    def _document_to_dict(self, document: DocumentInDB) -> dict:
        """Convert DocumentInDB to dictionary for storage."""
        data = document.model_dump()
        if data.get(Document.FIELD_DOCSOURCE_UUIDS):
            data[Document.FIELD_DOCSOURCE_UUIDS] = ",".join(
                data[Document.FIELD_DOCSOURCE_UUIDS]
            )
        if data.get(Document.FIELD_AUTO_SUMMARY):
            data[Document.FIELD_AUTO_SUMMARY] = json.dumps(
                data[Document.FIELD_AUTO_SUMMARY]
            )
        if data.get(Document.FIELD_MANUAL_SUMMARY):
            data[Document.FIELD_MANUAL_SUMMARY] = json.dumps(
                data[Document.FIELD_MANUAL_SUMMARY]
            )
        return data

    def _document_update_to_dict(self, document_update: DocumentUpdate) -> dict:
        """Convert DocumentUpdate to dictionary for query."""
        data = document_update.model_dump()
        if data.get(Document.FIELD_DOCSOURCE_UUIDS):
            data[Document.FIELD_DOCSOURCE_UUIDS] = ",".join(
                data[Document.FIELD_DOCSOURCE_UUIDS]
            )
        if data.get(Document.FIELD_AUTO_SUMMARY):
            data[Document.FIELD_AUTO_SUMMARY] = json.dumps(
                data[Document.FIELD_AUTO_SUMMARY]
            )
        if data.get(Document.FIELD_MANUAL_SUMMARY):
            data[Document.FIELD_MANUAL_SUMMARY] = json.dumps(
                data[Document.FIELD_MANUAL_SUMMARY]
            )
        return data

    def _get_documents_in_kb(
        self, org: Org, kb: KnowledgeBase, query: str
    ) -> List[Document]:
        """Get documents matching the query."""
        table_name = self._get_table_name(org, kb)

        if query:
            where_clause = f"WHERE {query}"
        else:
            where_clause = None

        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
        )

        return [self._dict_to_document(row) for row in results]

    def _get_table_name(self, org: Org, kb: KnowledgeBase) -> str:
        """Get the dynamic table name for the org and kb combination."""
        org_db_name = Org.get_org_db_name(org.org_id)
        collection_name = f"{kb.kb_id}{DOCUMENT_COLLECTION_SUFFIX}"
        return self.duckdb_client.create_table_if_not_exists(
            org_db_name,
            collection_name,
            DocumentDuckDBSchema.get_schema(),
        )

    def create_document(
        self, org: Org, kb: KnowledgeBase, document_create: DocumentCreate
    ) -> Optional[Document]:
        """Create a new document."""
        table_name = self._get_table_name(org, kb)
        document_in_store = DocumentInDB.from_document_create(document_create)
        document_in_store.document_uuid = str(uuid.uuid4())

        # Check for existing documents
        existing_docs = self._get_documents_in_kb(
            org,
            kb,
            (
                f"{DocSink.FIELD_DOCSINK_UUID} = '{document_in_store.docsink_uuid}' "
                f"AND {Document.FIELD_IS_DELETED} = False"
            ),
        )
        if existing_docs:
            logger().debug(
                f"Existing documents found for docsink_uuid: {document_in_store.docsink_uuid}. "
                f"{document_in_store.original_uri}. Marking them as deleted."
            )
            for doc in existing_docs:
                logger().debug(
                    f"Deleting document {doc.document_uuid} for {doc.original_uri}"
                )
                self.delete_document(org, kb, doc)

        # Insert new document
        data = self._document_to_dict(document_in_store)
        column_list = list(data.keys())
        value_list = list(data.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )

        return self.get_document_by_id(org, kb, document_in_store.document_uuid)

    def delete_document(self, org: Org, kb: KnowledgeBase, document: Document) -> bool:
        """Mark a document as deleted and clean up related data."""
        table_name = self._get_table_name(org, kb)
        doc_in_store = self.get_document_by_id(org, kb, document.document_uuid)

        if not doc_in_store:
            logger().warning(
                f"Document {document.document_uuid} not found for deletion"
            )
            return False

        # Update document status
        update_time = time_utils.current_datetime()
        column_list = [Document.FIELD_IS_DELETED, Document.FIELD_UPDATED_AT]
        where_clause = f"WHERE {Document.FIELD_DOCUMENT_UUID} = ?"
        value_list = [True, update_time, document.document_uuid]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        if not self.is_test:
            self._clean_up_related_data(org, kb, document)
        return True

    def get_document_by_id(
        self, org: Org, kb: KnowledgeBase, document_uuid: str
    ) -> Optional[Document]:
        """Get a document by its UUID."""
        documents = self._get_documents_in_kb(
            org, kb, f"{Document.FIELD_DOCUMENT_UUID} = '{document_uuid}'"
        )

        if not documents:
            return None

        assert len(documents) == 1
        return documents[0]

    def get_document_ids_for_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[str]:
        """Get document IDs for a docsource."""
        documents = self.get_documents_for_docsource(org, kb, docsource)
        return [doc.document_uuid for doc in documents]

    def get_documents_for_docsink(
        self, org: Org, kb: KnowledgeBase, docsink: DocSink
    ) -> List[Document]:
        """Get all non-deleted documents for a docsink."""
        return self._get_documents_in_kb(
            org,
            kb,
            (
                f"{DocSink.FIELD_DOCSINK_UUID} = '{docsink.docsink_uuid}' "
                f"AND {Document.FIELD_IS_DELETED} = False"
            ),
        )

    def get_documents_for_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[Document]:
        """Get all non-deleted documents for a docsource."""
        from leettools.context_manager import ContextManager

        context = ContextManager().get_context()

        docsink_store = context.get_repo_manager().get_docsink_store()
        docsinks = docsink_store.get_docsinks_for_docsource(org, kb, docsource)

        # see the logic in create_docsink, when we reuse docsinks
        # we only add docsource_uuid to the docsink not the document

        documents: List[Document] = []
        for docsink in docsinks:
            documents += self.get_documents_for_docsink(org, kb, docsink)
        return documents

    def get_documents_for_kb(self, org: Org, kb: KnowledgeBase) -> List[Document]:
        """Get all non-deleted documents for a knowledge base."""
        return self._get_documents_in_kb(
            org, kb, f"{Document.FIELD_IS_DELETED} = False"
        )

    def update_document(
        self, org: Org, kb: KnowledgeBase, document_update: DocumentUpdate
    ) -> Optional[Document]:
        """Update an existing document."""
        table_name = self._get_table_name(org, kb)

        data = self._document_update_to_dict(document_update)

        document_uuid = data.pop(Document.FIELD_DOCUMENT_UUID)
        column_list = list(data.keys())
        where_clause = f"WHERE {Document.FIELD_DOCUMENT_UUID} = ?"
        value_list = list(data.values()) + [document_uuid]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_document_by_id(org, kb, document_uuid)
