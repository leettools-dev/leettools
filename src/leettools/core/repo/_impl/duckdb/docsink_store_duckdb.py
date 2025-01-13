import uuid
from datetime import datetime
from typing import Any, List, Optional

from leettools.common import exceptions
from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger
from leettools.common.utils import time_utils
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

_DOCSINK_COLLECTION_SUFFIX = "_docsinks"


class DocsinkStoreDuckDB(AbstractDocsinkStore):
    """DocSinkStore implementation using DuckDB as the backend."""

    def __init__(self, settings: SystemSettings, is_test: bool = False) -> None:
        """Initialize DuckDB connection."""
        self.settings = settings
        self.is_test = is_test
        self.duckdb_client = DuckDBClient(settings)

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

        if DocSink.FIELD_ORIGINAL_DOC_URI in data:
            data[DocSink.FIELD_ORIGINAL_DOC_URI] = str(
                data[DocSink.FIELD_ORIGINAL_DOC_URI]
            )
        if DocSink.FIELD_RAW_DOC_URI in data:
            data[DocSink.FIELD_RAW_DOC_URI] = str(data[DocSink.FIELD_RAW_DOC_URI])

        if data.get(DocSink.FIELD_DOCSINK_STATUS):
            data[DocSink.FIELD_DOCSINK_STATUS] = data[
                DocSink.FIELD_DOCSINK_STATUS
            ].value
        if data.get(DocSink.FIELD_DOCSOURCE_UUIDS):
            if type(data[DocSink.FIELD_DOCSOURCE_UUIDS]) == list:
                data[DocSink.FIELD_DOCSOURCE_UUIDS] = ",".join(
                    data[DocSink.FIELD_DOCSOURCE_UUIDS]
                )
            elif type(data[DocSink.FIELD_DOCSOURCE_UUIDS]) == str:
                pass
            else:
                raise exceptions.UnexpectedOperationFailureException(
                    operation_desc="Error converting DocSink to dict",
                    error=f"Unexpected type for docsource_uuids: {data[DocSink.FIELD_DOCSOURCE_UUIDS]}",
                )
        return data

    def _dict_to_docsink(self, data: dict) -> DocSink:
        """Convert stored dictionary to DocSink."""
        if data.get(DocSink.FIELD_DOCSINK_STATUS):
            data[DocSink.FIELD_DOCSINK_STATUS] = DocSinkStatus(
                data[DocSink.FIELD_DOCSINK_STATUS]
            )
        if data.get(DocSink.FIELD_DOCSOURCE_UUIDS):
            uuids = data[DocSink.FIELD_DOCSOURCE_UUIDS]
            if type(uuids) == str:
                data[DocSink.FIELD_DOCSOURCE_UUIDS] = uuids.split(",")
            elif type(uuids) == list:
                pass
            else:
                raise exceptions.UnexpectedOperationFailureException(
                    operation_desc="Error converting dict to DocSink",
                    error=f"Unexpected type for docsource_uuids: {uuids}",
                )

        return DocSink.from_docsink_in_db(DocSinkInDB.model_validate(data))

    def _get_table_name(self, org: Org, kb: KnowledgeBase) -> str:
        """Get the dynamic table name for the org and kb combination."""
        org_db_name = Org.get_org_db_name(org.org_id)
        collection_name = f"{kb.kb_id}{_DOCSINK_COLLECTION_SUFFIX}"
        return self.duckdb_client.create_table_if_not_exists(
            org_db_name,
            collection_name,
            DocsinkDuckDBSchema.get_schema(),
        )

    def _get_docsinks_in_kb(
        self,
        org: Org,
        kb: KnowledgeBase,
        column_list: List[str] = None,
        value_list: List[Any] = None,
        where_clause: str = None,
    ) -> List[DocSink]:
        table_name = self._get_table_name(org, kb)
        docsink_dicts = self.duckdb_client.fetch_all_from_table(
            table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        docsinks = []
        if docsink_dicts:
            for docsink_dict in docsink_dicts:
                docsink = self._dict_to_docsink(docsink_dict)
                docsinks.append(docsink)
        return docsinks

    def create_docsink(
        self, org: Org, kb: KnowledgeBase, docsink_create: DocSinkCreate
    ) -> Optional[DocSink]:
        """Create a new docsink."""
        table_name = self._get_table_name(org, kb)

        docsink_in_db = DocSinkInDB.from_docsink_create(docsink_create)
        docsink_dict = self._docsink_to_dict(docsink_in_db)

        # make sure the original_doc_uri and raw_doc_uri are strings
        def _create_helper(
            existing_docsinks: Optional[List[DocSink]] = [],
        ) -> Optional[DocSink]:
            docsink_uuid = str(uuid.uuid4())
            docsink_dict[DocSink.FIELD_DOCSINK_UUID] = docsink_uuid

            column_list = list(docsink_dict.keys())
            value_list = list(docsink_dict.values())
            self.duckdb_client.insert_into_table(
                table_name=table_name,
                column_list=column_list,
                value_list=value_list,
            )
            result = self.get_docsink_by_id(org, kb, docsink_uuid)

            if result is not None:
                logger().debug(f"Successfllly created a new DocSink: {docsink_uuid}.")
                creation_time = result.created_at
                for existing in existing_docsinks:
                    if existing.expired_at is None:
                        existing.expired_at = creation_time
                        self.update_docsink(org, kb, existing)
                return result
            else:
                raise exceptions.UnexpectedOperationFailureException(
                    operation_desc="Error creating DocSink",
                    error=f"Failed to create DocSink {docsink_uuid}: {docsink_dict}",
                )

        # check if the original_doc_uri already has docsinks in this KB
        ori_doc_uri = docsink_dict[DocSink.FIELD_ORIGINAL_DOC_URI]
        existing_docsinks = self._get_docsinks_in_kb(
            org=org,
            kb=kb,
            column_list=None,
            value_list=[ori_doc_uri],
            where_clause=(
                f"WHERE {DocSink.FIELD_ORIGINAL_DOC_URI} = ? "
                f"AND {DocSink.FIELD_IS_DELETED} = False"
            ),
        )
        if len(existing_docsinks) == 0:
            logger().debug(
                f"No existing DocSink found, creating new DocSink: {ori_doc_uri}"
            )
            return _create_helper(existing_docsinks)

        logger().debug(f"Found existing docsink for: {ori_doc_uri}")
        if docsink_create.raw_doc_hash is None:
            logger().debug(f"No raw_doc_hash, creating new DocSink: {ori_doc_uri}")
            return _create_helper(existing_docsinks)

        using_existing = None
        docsource_uuid = docsink_create.docsource.docsource_uuid
        for existing in existing_docsinks:
            if existing.raw_doc_hash == docsink_create.raw_doc_hash:
                logger().info(
                    f"Found existing DocSink with same hash: {existing.docsink_uuid} "
                )
                if existing.expired_at is not None:
                    logger().debug(
                        f"The existing DocSink has already expired: {existing.docsink_uuid} "
                    )
                else:
                    using_existing = existing
                    break
        if using_existing is not None:
            if docsource_uuid in using_existing.docsource_uuids:
                logger().debug(
                    f"DocSink already has docsource {using_existing.docsink_uuid}: {docsource_uuid}"
                )
            else:
                logger().debug(
                    f"Addin docsource id to docsink {using_existing.docsink_uuid}: {docsource_uuid}"
                )
                using_existing.docsource_uuids.append(docsource_uuid)
            using_existing.updated_at = time_utils.current_datetime()
            update_docsink = self.update_docsink(org, kb, using_existing)
            return update_docsink

        logger().debug("No existing docsink with same hash, creating new docsink")
        return _create_helper(existing_docsinks)

    def delete_docsink(self, org: Org, kb: KnowledgeBase, docsink: DocSink) -> bool:
        table_name = self._get_table_name(org, kb)
        column_list = [DocSink.FIELD_IS_DELETED, DocSink.FIELD_UPDATED_AT]
        value_list = [True, time_utils.current_datetime()]
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
        where_clause = f"WHERE {DocSink.FIELD_DOCSINK_UUID} = '{docsink_uuid}'"
        existing_dict = self.duckdb_client.fetch_one_from_table(
            table_name,
            where_clause=where_clause,
        )

        if existing_dict is not None:
            uuids = existing_dict[DocSink.FIELD_DOCSOURCE_UUIDS]
            return self._dict_to_docsink(existing_dict)
        return None

    def get_docsinks_for_kb(self, org: Org, kb: KnowledgeBase) -> List[DocSink]:
        table_name = self._get_table_name(org, kb)

        # Get column names from schema
        where_clause = (
            f"WHERE {DocSink.FIELD_IS_DELETED} = FALSE "
            f"AND {DocSink.FIELD_EXPIRED_AT} IS NULL"
        )
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
    ) -> List[DocSink]:
        table_name = self._get_table_name(org, kb)

        where_clause = (
            f"WHERE {DocSink.FIELD_DOCSOURCE_UUIDS} like ? "
            f"AND {DocSink.FIELD_IS_DELETED} = FALSE "
            f"AND {DocSink.FIELD_EXPIRED_AT} IS NULL"
        )
        value_list = [f"%{docsource.docsource_uuid}%"]
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )

        docsinks = [self._dict_to_docsink(row) for row in results]

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
