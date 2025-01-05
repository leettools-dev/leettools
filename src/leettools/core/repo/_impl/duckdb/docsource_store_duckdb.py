import json
import time
import uuid
from datetime import datetime
from typing import List, Optional

from leettools.common import exceptions
from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.repo._impl.duckdb.docsource_store_duckdb_schema import (
    DocSourceDuckDBSchema,
)
from leettools.core.repo.docsource_store import AbstractDocsourceStore
from leettools.core.schemas.docsource import (
    DocSource,
    DocSourceCreate,
    DocSourceInDB,
    DocSourceUpdate,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings

DOCSOURCE_COLLECTION_SUFFIX = "_docsources"


class DocsourceStoreDuckDB(AbstractDocsourceStore):
    """DocSourceStore implementation using DuckDB as the backend."""

    def __init__(self, settings: SystemSettings, is_test: bool = False) -> None:
        """Initialize DuckDB connection."""
        self.settings = settings
        self.is_test = is_test
        self.duckdb_client = DuckDBClient(self.settings)

    def _clean_up_related_data(self, org: Org, kb: KnowledgeBase, docsource: DocSource):
        """Clean up related data for a docsource."""
        from leettools.context_manager import Context, ContextManager

        context: Context = ContextManager().get_context()

        docsink_store = context.get_repo_manager().get_docsink_store()
        for docsink in docsink_store.get_docsinks_for_docsource(org, kb, docsource):
            docsink_store.delete_docsink(org, kb, docsink)

        task_store = context.get_task_manager().get_taskstore()
        for task in task_store.get_tasks_for_docsource(docsource.docsource_uuid):
            task_store.delete_task(task.task_uuid)

    def _get_table_name(self, org: Org, kb: KnowledgeBase) -> str:
        """Get the dynamic table name for the org and kb combination."""
        org_db_name = Org.get_org_db_name(org.org_id)
        collection_name = f"{kb.kb_id}{DOCSOURCE_COLLECTION_SUFFIX}"
        return self.duckdb_client.create_table_if_not_exists(
            org_db_name,
            collection_name,
            DocSourceDuckDBSchema.get_schema(),
        )

    def _docsource_to_dict(self, docsource: DocSourceInDB) -> dict:
        """Convert DocSourceInDB to dictionary for storage."""
        data = docsource.model_dump()
        if data.get("ingest_config"):
            data["ingest_config"] = json.dumps(data["ingest_config"])
        if data.get("schedule_config"):
            data["schedule_config"] = json.dumps(data["schedule_config"])
        if data.get("tags"):
            data["tags"] = json.dumps(data["tags"])
        if data.get(DocSource.FIELD_SOURCE_TYPE):
            data[DocSource.FIELD_SOURCE_TYPE] = data[DocSource.FIELD_SOURCE_TYPE].value
        if data.get(DocSource.FIELD_DOCSOURCE_STATUS):
            data[DocSource.FIELD_DOCSOURCE_STATUS] = data[
                DocSource.FIELD_DOCSOURCE_STATUS
            ].value
        return data

    def _dict_to_docsource(self, data: dict) -> DocSource:
        """Convert stored dictionary to DocSource."""
        if data.get("ingest_config"):
            data["ingest_config"] = json.loads(data["ingest_config"])
        if data.get("schedule_config"):
            data["schedule_config"] = json.loads(data["schedule_config"])
        if data.get("tags"):
            data["tags"] = json.loads(data["tags"])
        if data.get(DocSource.FIELD_DOCSOURCE_STATUS):
            data[DocSource.FIELD_DOCSOURCE_STATUS] = DocSourceStatus(
                data[DocSource.FIELD_DOCSOURCE_STATUS]
            )
        return DocSource.from_docsource_in_db(DocSourceInDB.model_validate(data))

    def create_docsource(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource_create: DocSourceCreate,
        init_status: DocSourceStatus = DocSourceStatus.CREATED,
    ) -> Optional[DocSource]:
        table_name = self._get_table_name(org, kb)
        # Check for existing docsource with same URI
        where_clause = (
            f"WHERE {DocSource.FIELD_URI} = ? AND {DocSource.FIELD_IS_DELETED} = FALSE"
        )
        value_list = [docsource_create.uri]
        existing_dict = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )

        if existing_dict:
            return self._dict_to_docsource(existing_dict)

        # Create new docsource
        docsource_in_db = DocSourceInDB.from_docsource_create(docsource_create)
        docsource_in_db.docsource_status = init_status
        data = self._docsource_to_dict(docsource_in_db)

        if not data.get(DocSource.FIELD_DOCSOURCE_UUID):
            data[DocSource.FIELD_DOCSOURCE_UUID] = str(uuid.uuid4())

        column_list = list(data.keys())
        value_list = list(data.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )

        return self.get_docsource(org, kb, data[DocSource.FIELD_DOCSOURCE_UUID])

    def delete_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> bool:
        table_name = self._get_table_name(org, kb)
        column_list = [
            DocSource.FIELD_IS_DELETED,
            DocSource.FIELD_DOCSOURCE_STATUS,
            DocSource.FIELD_UPDATED_AT,
        ]
        value_list = [True, DocSourceStatus.ABORTED, time_utils.current_datetime()]
        where_clause = (
            f"WHERE {DocSource.FIELD_DOCSOURCE_UUID} = '{docsource.docsource_uuid}'"
        )
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )

        if not self.is_test:
            self._clean_up_related_data(org, kb, docsource)
        return True

    def get_docsource(
        self, org: Org, kb: KnowledgeBase, docsource_uuid: str
    ) -> Optional[DocSource]:
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {DocSource.FIELD_DOCSOURCE_UUID} = ?"
        value_list = [docsource_uuid]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result:
            return self._dict_to_docsource(result)
        return None

    def get_docsources_for_kb(self, org: Org, kb: KnowledgeBase) -> List[DocSource]:
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {DocSource.FIELD_KB_ID} = ? AND {DocSource.FIELD_IS_DELETED} = FALSE"
        value_list = [kb.kb_id]
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_docsource(row) for row in results]

    def update_docsource(
        self, org: Org, kb: KnowledgeBase, docsource_update: DocSourceUpdate
    ) -> Optional[DocSource]:
        table_name = self._get_table_name(org, kb)

        docsource_in_db = DocSourceInDB.from_docsource_update(docsource_update)
        data = self._docsource_to_dict(docsource_in_db)

        excluded_cols = {DocSource.FIELD_DOCSOURCE_UUID}
        update_cols = [
            col
            for col in DocSourceDuckDBSchema.get_schema().keys()
            if col not in excluded_cols
        ]

        value_list = [data.get(col) for col in update_cols]
        where_clause = f"WHERE {DocSource.FIELD_DOCSOURCE_UUID} = '{data[DocSource.FIELD_DOCSOURCE_UUID]}'"
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=update_cols,
            value_list=value_list,
            where_clause=where_clause,
        )

        return self.get_docsource(org, kb, data[DocSource.FIELD_DOCSOURCE_UUID])

    def wait_for_docsource(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        timeout_in_secs: Optional[int] = 300,
    ) -> bool:
        """Wait for a docsource to finish processing."""
        if timeout_in_secs is not None:
            logger().info(
                f"Waiting for docsource {docsource.docsource_uuid} to be processed. "
                f"Checking every 5 seconds. Timeout is set to {timeout_in_secs} seconds."
            )
        else:
            logger().info(
                f"Waiting for docsource {docsource.docsource_uuid} to be processed. "
                "Checking every 5 seconds. No timeout is set."
            )

        process_finished = False
        wait_time = 0
        while not process_finished:
            docsource_retrieved = self.get_docsource(org, kb, docsource.docsource_uuid)
            if docsource_retrieved is not None:
                if docsource_retrieved.is_finished():
                    process_finished = True
                    logger().info(
                        f"Finished processing docsource {docsource.docsource_uuid} "
                        f"after {wait_time} seconds, "
                        f"status {docsource_retrieved.docsource_status}."
                    )
                    break
            else:
                raise exceptions.UnexpectedCaseException(
                    f"Docsource {docsource.docsource_uuid} not found in the DB."
                )

            time.sleep(5)
            wait_time += 5
            if timeout_in_secs is None or wait_time < timeout_in_secs:
                continue

            logger().info(
                f"Timed out after {timeout_in_secs} seconds. "
                "Will continue with partial processed results."
            )
            break

        return process_finished
