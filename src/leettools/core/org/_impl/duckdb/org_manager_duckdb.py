import uuid
from datetime import datetime
from typing import List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.exceptions import EntityNotFoundException
from leettools.common.utils import time_utils
from leettools.core.org._impl.duckdb.org_duckdb_schema import OrgDuckDBSchema
from leettools.core.org.org_manager import AbstractOrgManager
from leettools.core.schemas.organization import Org, OrgCreate, OrgInDB, OrgUpdate
from leettools.settings import SystemSettings


class OrgManagerDuckDB(AbstractOrgManager):
    """
    This is a DuckDB implementation that only have one default org.
    """

    def __init__(self, settings: SystemSettings) -> None:
        self.settings = settings
        self.default_org = Org(
            name=settings.DEFAULT_ORG_NAME,
            org_id=settings.DEFAULT_ORG_ID,
            description="Default organization for testing purposes.",
        )
        self.duckdb_client = DuckDBClient(self.settings)
        self.table_name = self._create_table()

    def _create_table(self) -> str:
        return self.duckdb_client.create_table_if_not_exists(
            self.settings.DB_COMMOM,
            self.settings.COLLECTION_ORG,
            OrgDuckDBSchema.get_schema(),
        )

    def _clear_test_orgs(self) -> None:
        if self.settings.DUCKDB_FILE.endswith("_test.db"):
            self.duckdb_client.delete_from_table(table_name=self.table_name)

    def get_default_org(self) -> Org:
        return self.default_org

    def add_org(self, org_create: OrgCreate) -> Org:
        org_in_db = OrgInDB.from_org_create(org_create)
        org_dict = org_in_db.model_dump()
        org_dict[Org.FIELD_ORG_ID] = str(uuid.uuid4())
        if Org.FIELD_ORG_STATUS in org_dict:
            org_dict[Org.FIELD_ORG_STATUS] = org_dict[Org.FIELD_ORG_STATUS].value
        column_list = list(org_dict.keys())
        value_list = list(org_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
        )
        org_in_db.org_id = org_dict[Org.FIELD_ORG_ID]
        return Org.from_org_in_db(org_in_db)

    def delete_org_by_id(self, org_id: str) -> bool:
        where_clause = f"WHERE {Org.FIELD_ORG_ID} = ?"
        value_list = [org_id]
        self.duckdb_client.delete_from_table(
            table_name=self.table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def delete_org_by_name(self, org_name: str) -> bool:
        org = self.get_org_by_name(org_name)
        if org is None:
            raise EntityNotFoundException(org_name, "Org")

        return self.delete_org_by_id(org.org_id)

    def get_org_by_id(self, org_id: str) -> Optional[Org]:
        if org_id == self.default_org.org_id:
            return self.default_org

        select_sql = f"WHERE {Org.FIELD_ORG_ID} = ?"
        value_list = [org_id]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=select_sql,
            value_list=value_list,
        )
        if rtn_dict is not None:
            return Org.from_org_in_db(OrgInDB.model_validate(rtn_dict))
        return None

    def get_org_by_name(self, org_name: str) -> Optional[Org]:
        if org_name == self.default_org.name:
            return self.default_org

        select_sql = f"WHERE {Org.FIELD_NAME} = ?"
        value_list = [org_name]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=self.table_name,
            where_clause=select_sql,
            value_list=value_list,
        )
        if rtn_dict is not None:
            return Org.from_org_in_db(OrgInDB.model_validate(rtn_dict))
        return None

    def list_orgs(self) -> List[Org]:
        orgs = [self.default_org]
        rtn_dicts = self.duckdb_client.fetch_all_from_table(table_name=self.table_name)
        for rtn_dict in rtn_dicts:
            orgs.append(Org.from_org_in_db(OrgInDB.model_validate(rtn_dict)))
        return orgs

    def update_org(self, org_update: OrgUpdate) -> Optional[Org]:
        org_update_dict = org_update.model_dump()
        if Org.FIELD_ORG_STATUS in org_update_dict:
            org_update_dict[Org.FIELD_ORG_STATUS] = org_update_dict[
                Org.FIELD_ORG_STATUS
            ].value

        org_id = org_update_dict.pop(Org.FIELD_ORG_ID)
        column_list = list(org_update_dict.keys()) + [Org.FIELD_UPDATED_AT]
        value_list = list(org_update_dict.values()) + [time_utils.current_datetime()]
        where_clause = f"WHERE {Org.FIELD_ORG_ID} = ?"
        value_list = value_list + [org_id]
        self.duckdb_client.update_table(
            table_name=self.table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_org_by_id(org_id)
