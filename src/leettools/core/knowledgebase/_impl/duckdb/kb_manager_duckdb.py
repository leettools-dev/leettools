import json
import uuid
from typing import Dict, List, Optional

from leettools.common import exceptions
from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.knowledgebase._impl.duckdb.kb_duckdb_schema import KBDuckDBSchema
from leettools.core.knowledgebase.kb_manager import AbstractKBManager
from leettools.core.repo.repo_manager import RepoManager
from leettools.core.schemas.knowledgebase import (
    KBCreate,
    KBInDB,
    KBPerfConfig,
    KBUpdate,
    KnowledgeBase,
)
from leettools.core.schemas.organization import Org
from leettools.core.user.user_store import AbstractUserStore
from leettools.eds.str_embedder.utils.embedder_settings import (
    set_kb_create_embedder_params,
)
from leettools.settings import SystemSettings


class KBManagerDuckDB(AbstractKBManager):
    """
    KBManagerDuckDB is a KBManager implementation using DuckDB as the backend.
    """

    def __init__(self, settings: SystemSettings) -> None:
        """
        Initialize the DuckDB.
        """
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)

    def _dict_to_kb(self, kb_dict: Dict) -> KnowledgeBase:
        kb_dict = kb_dict.copy()
        if KnowledgeBase.FIELD_DENSE_EMBEDDER_PARAMS in kb_dict:
            kb_dict[KnowledgeBase.FIELD_DENSE_EMBEDDER_PARAMS] = json.loads(
                kb_dict[KnowledgeBase.FIELD_DENSE_EMBEDDER_PARAMS]
            )
        if KnowledgeBase.FIELD_SPARSE_EMBEDDER_PARAMS in kb_dict:
            kb_dict[KnowledgeBase.FIELD_SPARSE_EMBEDDER_PARAMS] = json.loads(
                kb_dict[KnowledgeBase.FIELD_SPARSE_EMBEDDER_PARAMS]
            )
        if KnowledgeBase.FIELD_PROMOTION_METADATA in kb_dict:
            kb_dict[KnowledgeBase.FIELD_PROMOTION_METADATA] = json.loads(
                kb_dict[KnowledgeBase.FIELD_PROMOTION_METADATA]
            )
        return KnowledgeBase.model_validate(kb_dict)

    def _get_table_name(self, org: Org) -> str:
        org_db_name = Org.get_org_db_name(org.org_id)
        db_name = org_db_name
        table_name = self.settings.COLLECTION_KB
        return self.duckdb_client.create_table_if_not_exists(
            db_name,
            table_name,
            KBDuckDBSchema.get_schema(),
        )

    def _kb_to_dict(self, kb: KnowledgeBase) -> Dict:
        kb_dict = kb.model_dump()
        if KnowledgeBase.FIELD_DENSE_EMBEDDER_PARAMS in kb_dict:
            kb_dict[KnowledgeBase.FIELD_DENSE_EMBEDDER_PARAMS] = json.dumps(
                kb_dict[KnowledgeBase.FIELD_DENSE_EMBEDDER_PARAMS]
            )
        if KnowledgeBase.FIELD_SPARSE_EMBEDDER_PARAMS in kb_dict:
            kb_dict[KnowledgeBase.FIELD_SPARSE_EMBEDDER_PARAMS] = json.dumps(
                kb_dict[KnowledgeBase.FIELD_SPARSE_EMBEDDER_PARAMS]
            )
        if KnowledgeBase.FIELD_PROMOTION_METADATA in kb_dict:
            kb_dict[KnowledgeBase.FIELD_PROMOTION_METADATA] = json.dumps(
                kb_dict[KnowledgeBase.FIELD_PROMOTION_METADATA]
            )
        return kb_dict

    def _get_user_store(self) -> AbstractUserStore:
        # this is kind of hacky to avoid circular import
        from leettools.context_manager import Context, ContextManager

        context = ContextManager().get_context()  # type: Context

        return context.get_user_store()

    def _get_repo_manager(self) -> RepoManager:
        # this is kind of hacky to avoid circular import
        from leettools.context_manager import Context, ContextManager

        context = ContextManager().get_context()
        return context.get_repo_manager()

    def _from_kb_in_db(self, kb_dict: Dict) -> KnowledgeBase:
        """
        Convert KBInDB to KnowledgeBase.
        """
        kb = self._dict_to_kb(kb_dict)
        if kb.user_uuid is not None:
            user = self._get_user_store().get_user_by_uuid(kb.user_uuid)
            if user is not None:
                kb.user = user.username
            else:
                logger().warning(
                    f"User with UUID {kb.user_uuid} not found"
                    f" for knowledge base {kb.name}"
                )
        if kb.owner_id is not None:
            owner = self._get_user_store().get_user_by_uuid(kb.owner_id)
            if owner is not None:
                kb.owner = owner.username
            else:
                logger().warning(
                    f"Owner with UUID {kb.owner_id} not found"
                    f" for knowledge base {kb.name}"
                )
        return kb

    def add_kb(self, org: Org, kb_create: KBCreate) -> KnowledgeBase:
        """
        Adds a new knowledge base entry.

        Args:
        - org: The organization to which the knowledge base belongs.
        - kb_create: The knowledge base to add.

        Returns:
        - The added knowledge base.
        """
        kb_create = set_kb_create_embedder_params(kb_create)
        self.record_perf_config(KBPerfConfig.from_base_model(kb_create))

        kb_in_db = KBInDB.from_kb_create(kb_create)
        rtn_kb = self.get_kb_by_name(org=org, kb_name=kb_in_db.name)
        if rtn_kb is not None:
            raise exceptions.EntityExistsException(kb_in_db.name, "KnowledgeBase")

        table_name = self._get_table_name(org)

        # TODO: reuse all the above storage-agnostic logic
        kb_dict = self._kb_to_dict(kb_in_db)
        kb_dict[KnowledgeBase.FIELD_KB_ID] = str(uuid.uuid4())

        column_list = list(kb_dict.keys())
        value_list = list(kb_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return self.get_kb_by_id(org, kb_dict[KnowledgeBase.FIELD_KB_ID])

    def delete_kb_by_name(self, org: Org, kb_name: str) -> bool:
        """
        Deletes a knowledge base entry.
        """
        kb_in_db = self.get_kb_by_name(org=org, kb_name=kb_name)
        if kb_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=kb_name, entity_type="KnowledgeBase"
            )

        table_name = self._get_table_name(org)
        kb_delete = kb_in_db.model_copy()
        kb_delete.name = kb_name + "_deleted_" + str(time_utils.current_datetime())
        kb_delete.updated_at = time_utils.current_datetime()
        kb_delete.is_deleted = True

        kb_dict = self._kb_to_dict(kb_delete)

        column_list = [k for k in kb_dict.keys() if k != KnowledgeBase.FIELD_KB_ID]
        value_list = [
            kb_dict[k] for k in kb_dict.keys() if k != KnowledgeBase.FIELD_KB_ID
        ]
        where_clause = f"WHERE {KnowledgeBase.FIELD_KB_ID} = ?"
        value_list = value_list + [kb_in_db.kb_id]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )

        # TODO: stop all the tasks for the knowledge base

        docsource_store = self._get_repo_manager().get_docsource_store()
        for docsource in docsource_store.get_docsources_for_kb(org, kb_in_db):
            docsource_store.delete_docsource(org, kb_in_db, docsource)
        return True

    def get_all_kbs_for_org(
        self, org: Org, list_adhoc: Optional[bool] = False
    ) -> List[KnowledgeBase]:
        """
        Gets all knowledge base entries for an organization.
        """
        table_name = self._get_table_name(org)
        select_sql = f"WHERE {KnowledgeBase.FIELD_IS_DELETED} = FALSE"
        if not list_adhoc:
            select_sql += f" AND {KnowledgeBase.FIELD_NAME} NOT LIKE 'adhoc_%'"
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=select_sql,
        )
        return [self._from_kb_in_db(rtn_dict) for rtn_dict in rtn_dicts]

    def get_kb_by_id(self, org: Org, kb_id: str) -> Optional[KnowledgeBase]:
        """
        Gets a knowledge base entry by its ID.
        """
        table_name = self._get_table_name(org)
        select_sql = f"WHERE {KnowledgeBase.FIELD_KB_ID} = ?"
        value_list = [kb_id]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=select_sql,
            value_list=value_list,
        )
        if rtn_dict is None:
            return None
        return self._from_kb_in_db(rtn_dict)

    def get_kb_by_name(self, org: Org, kb_name: str) -> Optional[KnowledgeBase]:
        """
        Gets a knowledge base entry by its ID.
        """
        table_name = self._get_table_name(org)
        select_sql = f"WHERE {KnowledgeBase.FIELD_NAME} = ?"
        value_list = [kb_name]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=select_sql,
            value_list=value_list,
        )
        if rtn_dict is None:
            return None
        return self._from_kb_in_db(rtn_dict)

    def update_kb(self, org: Org, kb_update: KBUpdate) -> Optional[KnowledgeBase]:
        """
        Updates an existing knowledge base entry.

        Use rename to change the name of the knowledge base.
        """
        kb_in_db = self.get_kb_by_name(org=org, kb_name=kb_update.name)
        if kb_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=kb_update.name, entity_type="KnowledgeBase"
            )

        if kb_update.new_name is not None and kb_update.new_name != "":
            if kb_update.new_name == kb_update.name:
                logger().info(
                    "Specified new name the same as the current name, no change."
                )
            else:
                target_kb_in_db = self.get_kb_by_name(
                    org=org, kb_name=kb_update.new_name
                )
                if target_kb_in_db is not None:
                    raise exceptions.EntityExistsException(
                        kb_update.new_name, "KnowledgeBase"
                    )
                else:
                    logger().info(
                        f"Trying to rename knowledge base from {kb_in_db.name} to {kb_update.new_name}"
                    )
                    kb_update.name = kb_update.new_name

        table_name = self._get_table_name(org)

        kb_update_dict = kb_update.model_dump(exclude_unset=True)
        if KnowledgeBase.FIELD_PROMOTION_METADATA in kb_update_dict:
            kb_update_dict[KnowledgeBase.FIELD_PROMOTION_METADATA] = json.dumps(
                kb_update_dict[KnowledgeBase.FIELD_PROMOTION_METADATA]
            )

        column_list = [
            k
            for k in kb_update_dict.keys()
            if k != KnowledgeBase.FIELD_KB_ID and k != KBUpdate.FIELD_NEW_NAME
        ]
        value_list = [
            kb_update_dict[k]
            for k in kb_update_dict.keys()
            if k != KnowledgeBase.FIELD_KB_ID and k != KBUpdate.FIELD_NEW_NAME
        ]
        column_list = column_list + [KnowledgeBase.FIELD_UPDATED_AT]
        value_list = value_list + [time_utils.current_datetime()]

        where_clause = f"WHERE {KnowledgeBase.FIELD_KB_ID} = ?"
        value_list = value_list + [kb_in_db.kb_id]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_kb_by_id(org, kb_in_db.kb_id)

    def update_kb_timestamp(
        self, org: Org, kb: KnowledgeBase
    ) -> Optional[KnowledgeBase]:
        kb_in_db = self.get_kb_by_name(org=org, kb_name=kb.name)
        if kb_in_db is None:
            raise exceptions.EntityNotFoundException(
                entity_name=kb.name, entity_type="KnowledgeBase"
            )

        table_name = self._get_table_name(org)
        column_list = [KnowledgeBase.FIELD_UPDATED_AT]
        value_list = [time_utils.current_datetime()]
        where_clause = f"WHERE {KnowledgeBase.FIELD_KB_ID} = ?"
        value_list = value_list + [kb_in_db.kb_id]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_kb_by_id(org, kb_in_db.kb_id)
