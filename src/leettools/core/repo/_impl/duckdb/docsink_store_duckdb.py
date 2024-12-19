import json
import uuid
from datetime import datetime
from typing import List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.repo._impl.duckdb.docsink_store_duckdb_schema import (
    DocsinkDuckDBSchema,
)
from leettools.core.repo.docsink_store import AbstractDocsinkStore
from leettools.core.schemas.docsink import (
    DocSink,
    DocSinkCreate,
    DocSinkInDB,
    DocSinkUpdate,
)
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings

DOCSINK_COLLECTION_SUFFIX = "_docsinks"


class DocsinkStoreDuckDB(AbstractDocsinkStore):
    """DocSinkStore implementation using DuckDB as the backend."""

    def __init__(self, settings: SystemSettings, is_test: bool = False) -> None:
        """Initialize DuckDB connection."""
        self.settings = settings
        self.is_test = is_test
        self.duckdb_client = DuckDBClient(settings)

    def _add_extra_original_doc_uri(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsink: DocSink,
        original_doc_uri: str,
        extra_docsource_uuid: str,
    ) -> DocSink:
        """Add extra original doc URI to a docsink."""
        need_update = False

        if docsink.extra_original_doc_uri is None:
            docsink.extra_original_doc_uri = [original_doc_uri]
            need_update = True
        else:
            if original_doc_uri not in docsink.extra_original_doc_uri:
                docsink.extra_original_doc_uri.append(original_doc_uri)
                need_update = True
            else:
                logger().info(
                    f"original_doc_uri {original_doc_uri} already exists in extra_original_doc_uri"
                )

        if docsink.extra_docsource_uuid is None:
            docsink.extra_docsource_uuid = [extra_docsource_uuid]
            need_update = True
        else:
            if extra_docsource_uuid not in docsink.extra_docsource_uuid:
                docsink.extra_docsource_uuid.append(extra_docsource_uuid)
                need_update = True
            else:
                logger().info(
                    f"extra_docsource_uuid {extra_docsource_uuid} already exists in extra_docsource_uuid"
                )

        if need_update:
            return self.update_docsink(org, kb, docsink)
        return docsink

    def _clean_up_related_data(self, org: Org, kb: KnowledgeBase, docsink: DocSink):
        """Clean up related data for a docsink."""
        from leettools.context_manager import Context, ContextManager

        context: Context = ContextManager().get_context()
        doc_store = context.get_repo_manager().get_document_store()
        for doc in doc_store.get_documents_for_docsink(org, kb, docsink):
            doc_store.delete_document(org, kb, doc)

        task_store = context.get_task_manager().get_taskstore()
        for task in task_store.get_tasks_for_docsink(docsink.docsink_uuid):
            task_store.delete_task(task.task_uuid)

    def _docsink_to_dict(self, docsink: DocSinkInDB) -> dict:
        """Convert DocSinkInDB to dictionary for storage."""
        data = docsink.model_dump()
        if data.get(DocSink.FIELD_EXTRA_ORIGINAL_DOC_URI):
            data[DocSink.FIELD_EXTRA_ORIGINAL_DOC_URI] = json.dumps(
                data[DocSink.FIELD_EXTRA_ORIGINAL_DOC_URI]
            )
        if data.get(DocSink.FIELD_EXTRA_DOCSOURCE_UUID):
            data[DocSink.FIELD_EXTRA_DOCSOURCE_UUID] = json.dumps(
                data[DocSink.FIELD_EXTRA_DOCSOURCE_UUID]
            )
        if data.get(DocSink.FIELD_DOCSINK_STATUS):
            data[DocSink.FIELD_DOCSINK_STATUS] = data[
                DocSink.FIELD_DOCSINK_STATUS
            ].value
        return data

    def _dict_to_docsink(self, data: dict) -> DocSink:
        """Convert stored dictionary to DocSink."""
        if data.get(DocSink.FIELD_EXTRA_ORIGINAL_DOC_URI):
            data[DocSink.FIELD_EXTRA_ORIGINAL_DOC_URI] = json.loads(
                data[DocSink.FIELD_EXTRA_ORIGINAL_DOC_URI]
            )
        if data.get(DocSink.FIELD_EXTRA_DOCSOURCE_UUID):
            data[DocSink.FIELD_EXTRA_DOCSOURCE_UUID] = json.loads(
                data[DocSink.FIELD_EXTRA_DOCSOURCE_UUID]
            )
        if data.get(DocSink.FIELD_DOCSINK_STATUS):
            data[DocSink.FIELD_DOCSINK_STATUS] = DocSinkStatus(
                data[DocSink.FIELD_DOCSINK_STATUS]
            )
        return DocSink.from_docsink_in_db(DocSinkInDB.model_validate(data))

    def _get_table_name(self, org: Org, kb: KnowledgeBase) -> str:
        """Get the dynamic table name for the org and kb combination."""
        org_db_name = Org.get_org_db_name(org.org_id)
        collection_name = f"{kb.kb_id}{DOCSINK_COLLECTION_SUFFIX}"
        return self.duckdb_client.create_table_if_not_exists(
            org_db_name,
            collection_name,
            DocsinkDuckDBSchema.get_schema(),
        )

    def create_docsink(
        self, org: Org, kb: KnowledgeBase, docsink_create: DocSinkCreate
    ) -> Optional[DocSink]:
        """Create a new docsink."""
        table_name = self._get_table_name(org, kb)

        # First check for existing docsink with same hash
        if docsink_create.raw_doc_hash:
            where_clause = f"WHERE {DocSink.FIELD_RAW_DOC_HASH} = ? AND {DocSink.FIELD_IS_DELETED} = FALSE"
            value_list = [docsink_create.raw_doc_hash]
            existing_dict = self.duckdb_client.fetch_one_from_table(
                table_name,
                where_clause=where_clause,
                value_list=value_list,
            )
            if existing_dict is not None:
                existing_docsink = self._dict_to_docsink(existing_dict)
                return self._add_extra_original_doc_uri(
                    org,
                    kb,
                    existing_docsink,
                    docsink_create.original_doc_uri,
                    docsink_create.docsource_uuid,
                )

        # Check for existing docsink with same URIs
        where_clause = (
            f"WHERE {DocSink.FIELD_ORIGINAL_DOC_URI} = ? "
            f"AND {DocSink.FIELD_RAW_DOC_URI} = ? "
            f"AND {DocSink.FIELD_KB_ID} = ? "
            f"AND {DocSink.FIELD_IS_DELETED} = FALSE"
        )
        value_list = [
            docsink_create.original_doc_uri,
            docsink_create.raw_doc_uri,
            docsink_create.kb_id,
        ]
        existing_dict = self.duckdb_client.fetch_one_from_table(
            table_name,
            where_clause=where_clause,
            value_list=value_list,
        )

        if existing_dict is not None:
            # Return existing docsink if found
            return self._dict_to_docsink(existing_dict)

        # Create new docsink if no existing one found
        docsink_in_db = DocSinkInDB.from_docsink_create(docsink_create)
        data = self._docsink_to_dict(docsink_in_db)

        # Generate UUID if not present
        if not data.get(DocSink.FIELD_DOCSINK_UUID):
            data[DocSink.FIELD_DOCSINK_UUID] = str(uuid.uuid4())

        column_list = list(data.keys())
        value_list = list(data.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return self.get_docsink_by_id(org, kb, data[DocSink.FIELD_DOCSINK_UUID])

    def delete_docsink(self, org: Org, kb: KnowledgeBase, docsink: DocSink) -> bool:
        table_name = self._get_table_name(org, kb)
        column_list = [DocSink.FIELD_IS_DELETED, DocSink.FIELD_UPDATED_AT]
        value_list = [True, datetime.now()]
        where_clause = f"WHERE {DocSink.FIELD_DOCSINK_UUID} = ?"
        value_list = value_list + [docsink.docsink_uuid]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )

        if not self.is_test:
            self._clean_up_related_data(org, kb, docsink)
        return True

    def get_docsink_by_id(
        self, org: Org, kb: KnowledgeBase, docsink_uuid: str
    ) -> Optional[DocSink]:
        table_name = self._get_table_name(org, kb)

        # Get column names from schema
        where_clause = f"WHERE {DocSink.FIELD_DOCSINK_UUID} = ?"
        value_list = [docsink_uuid]
        existing_dict = self.duckdb_client.fetch_one_from_table(
            table_name,
            where_clause=where_clause,
            value_list=value_list,
        )

        if existing_dict is not None:
            return self._dict_to_docsink(existing_dict)
        return None

    def get_docsinks_for_kb(self, org: Org, kb: KnowledgeBase) -> List[DocSink]:
        table_name = self._get_table_name(org, kb)

        # Get column names from schema
        where_clause = f"WHERE {DocSink.FIELD_IS_DELETED} = FALSE"
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
        )

        return [self._dict_to_docsink(row) for row in results]

    def get_docsinks_for_docsource(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        check_extra: bool = False,
    ) -> List[DocSink]:
        table_name = self._get_table_name(org, kb)

        where_clause = f"WHERE {DocSink.FIELD_DOCSOURCE_UUID} = ? AND {DocSink.FIELD_IS_DELETED} = FALSE"
        value_list = [docsource.docsource_uuid]
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )

        docsinks = [self._dict_to_docsink(row) for row in results]

        if check_extra:
            where_clause = (
                f"WHERE {DocSink.FIELD_EXTRA_DOCSOURCE_UUID} LIKE ? "
                f"AND {DocSink.FIELD_IS_DELETED} = FALSE"
            )
            value_list = [f"%{docsource.docsource_uuid}%"]
            extra_results = self.duckdb_client.fetch_all_from_table(
                table_name=table_name,
                where_clause=where_clause,
                value_list=value_list,
            )
            docsinks.extend([self._dict_to_docsink(row) for row in extra_results])
        return docsinks

    def update_docsink(
        self, org: Org, kb: KnowledgeBase, docsink_update: DocSinkUpdate
    ) -> Optional[DocSink]:
        """Update an existing docsink."""
        table_name = self._get_table_name(org, kb)

        docsink_in_db = DocSinkInDB.from_docsink_update(docsink_update)
        data = self._docsink_to_dict(docsink_in_db)

        # Get all columns except the primary key and any other columns we don't want to update
        excluded_cols = {
            DocSink.FIELD_DOCSINK_UUID
        }  # Add other columns to exclude if needed
        update_cols = [
            col
            for col in DocsinkDuckDBSchema.get_schema().keys()
            if col not in excluded_cols
        ]

        # Create SET clause and parameters list
        value_list = [data.get(col) for col in update_cols]
        where_clause = (
            f"WHERE {DocSink.FIELD_DOCSINK_UUID} = '{data[DocSink.FIELD_DOCSINK_UUID]}'"
        )
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=update_cols,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_docsink_by_id(org, kb, data[DocSink.FIELD_DOCSINK_UUID])
