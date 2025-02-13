import os
from datetime import datetime
from typing import List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.exceptions import EntityExistsException, EntityNotFoundException
from leettools.common.utils import time_utils
from leettools.core.strategy._impl.duckdb.intention_store_ducksb_schema import (
    IntentionDuckDBSchema,
)
from leettools.core.strategy.intention_store import AbstractIntentionStore
from leettools.core.strategy.schemas.intention import (
    Intention,
    IntentionCreate,
    IntentionUpdate,
)
from leettools.settings import SystemSettings

script_path = os.path.dirname(os.path.realpath(__file__))


class IntentionStoreDuckDB(AbstractIntentionStore):

    def __init__(
        self,
        settings: SystemSettings,
    ) -> None:
        """
        Initialize the DuckDB StrategyStore.
        """
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)

    def _dict_to_intention(self, data: dict) -> Intention:
        examples = data.get(Intention.FIELD_EXAMPLES, None)
        if examples is None or examples == "[]" or examples == "":
            data[Intention.FIELD_EXAMPLES] = []
        else:
            list_str = data[Intention.FIELD_EXAMPLES]
            list_str = list_str[1:-1]
            list = list_str.split(", ")
            data[Intention.FIELD_EXAMPLES] = list
        return Intention.model_validate(data)

    def _get_table_name(self) -> str:
        return self.duckdb_client.create_table_if_not_exists(
            self.settings.DB_COMMOM,
            self.settings.COLLECTION_INTENTIONS,
            IntentionDuckDBSchema.get_schema(),
        )

    def _intention_to_dict(self, intention: Intention) -> dict:
        intention_dict = intention.model_dump()
        if intention.examples is not None and len(intention.examples) > 0:
            intention_dict[Intention.FIELD_EXAMPLES] = (
                "[" + ", ".join(intention_dict[Intention.FIELD_EXAMPLES]) + "]"
            )
        return intention_dict

    def get_all_intentions(self) -> List[Intention]:
        intentions = []
        table_name = self._get_table_name()
        results = self.duckdb_client.fetch_all_from_table(table_name=table_name)
        for result in results:
            intentions.append(self._dict_to_intention(result))
        return intentions

    def get_intention_by_name(self, intention_name: str) -> Optional[Intention]:
        table_name = self._get_table_name()
        where_clause = f"WHERE {Intention.FIELD_INTENTION} = ?"
        value_list = [intention_name]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if result is None:
            return None
        return self._dict_to_intention(result)

    def create_intention(self, intention_create: IntentionCreate) -> Intention:
        # find if the intention already exists
        existing_intention = self.get_intention_by_name(intention_create.intention)
        if existing_intention is not None:
            raise EntityExistsException(
                entity_name=intention_create.intention,
                entity_type="Intention",
            )
        intention_dict = self._intention_to_dict(intention_create)

        if intention_create.display_name is None:
            intention_dict[Intention.FIELD_DISPLAY_NAME] = intention_create.intention
        intention_dict[Intention.FIELD_CREATED_AT] = time_utils.current_datetime()
        intention_dict[Intention.FIELD_UPDATED_AT] = intention_dict[
            Intention.FIELD_CREATED_AT
        ]

        table_name = self._get_table_name()
        column_list = list(intention_dict.keys())
        value_list = list(intention_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return self.get_intention_by_name(intention_create.intention)

    def update_intention(self, intention_update: IntentionUpdate) -> Intention:
        existing_intention = self.get_intention_by_name(intention_update.intention)
        if existing_intention is None:
            raise EntityNotFoundException(
                entity_name=intention_update.intention,
                entity_type="Intention",
            )

        intention_dict = self._intention_to_dict(intention_update)
        intention_dict[Intention.FIELD_UPDATED_AT] = time_utils.current_datetime()
        table_name = self._get_table_name()
        column_list = list(intention_dict.keys())
        value_list = list(intention_dict.values())
        where_clause = (
            f"WHERE {Intention.FIELD_INTENTION} = '{intention_update.intention}'"
        )
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return self.get_intention_by_name(intention_update.intention)

    def _reset_for_test(self):
        if self.settings.DUCKDB_FILE.endswith("_test.db"):
            table_name = self._get_table_name()
            self.duckdb_client.delete_from_table(table_name=table_name)
