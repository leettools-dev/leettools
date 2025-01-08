from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.duckdb.duckdb_schema_utils import (
    duckdb_data_to_pydantic_obj,
    pydantic_to_duckdb_schema,
)
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.extract.extract_store import (
    EXTRACT_DB_METADATA_FIELD,
    EXTRACT_DB_SOURCE_FIELD,
    EXTRACT_DB_TIMESTAMP_FIELD,
    AbstractExtractStore,
    get_extended_model,
)
from leettools.eds.rag.search.filter import BaseCondition, Filter
from leettools.eds.rag.search.filter_duckdb import to_duckdb_filter
from leettools.flow.metadata.extract_metadata_manager import (
    create_extraction_metadata_manager,
)
from leettools.flow.schemas.extract_metadata import ExtractMetadata


class ExtractStoreDuckdb(AbstractExtractStore):

    def __init__(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
        target_model_name: str,
        target_model_class: Type[TypeVar_BaseModel],
    ):
        super().__init__(context, org, kb, target_model_name, target_model_class)
        settings = context.settings

        self.collection_name = kb.collection_name_for_extracted_data(target_model_name)
        org_db_name = Org.get_org_db_name(org.org_id)

        self.extended_model_class = get_extended_model(
            target_model_name, target_model_class
        )
        self.columns = pydantic_to_duckdb_schema(self.extended_model_class)
        self.duckdb_client = DuckDBClient(settings)

        self.duckdb_table_name = self.duckdb_client.create_table_if_not_exists(
            schema_name=org_db_name,
            table_name=self.collection_name,
            columns=self.columns,
        )

        extract_metadata_manager = create_extraction_metadata_manager(settings)
        extract_metadata_manager.add_extracted_db_info(
            org=org,
            kb=kb,
            info=ExtractMetadata(
                db_type="duckdb",
                db_uri=f"duckdb://{settings.DUCKDB_PATH}/{org_db_name}/{self.collection_name}",
                target_model_name=target_model_name,
                target_model_schema_dict=self.extended_model_class.model_json_schema(),
                key_fields=[],  # TODO: add key fields
                verify_fields=[],
                item_count=0,
                created_at=time_utils.current_datetime(),
            ),
        )

    def save_records(
        self, records: List[TypeVar_BaseModel], metadata: Dict[str, Any]
    ) -> List[TypeVar_BaseModel]:
        created_timestamp_in_ms = time_utils.cur_timestamp_in_ms()

        new_obj_dicts: List[Dict[str, Any]] = []
        new_objs: List[self.extended_model_class] = []

        for record in records:
            try:
                obj_dict = record.model_dump()
                source = metadata.pop(EXTRACT_DB_SOURCE_FIELD, None)
                obj_dict[EXTRACT_DB_METADATA_FIELD] = metadata
                obj_dict[EXTRACT_DB_TIMESTAMP_FIELD] = created_timestamp_in_ms
                obj_dict[EXTRACT_DB_SOURCE_FIELD] = source

                new_obj = self.extended_model_class.model_validate(obj_dict)
                new_objs.append(new_obj)
                new_obj_dicts.append(obj_dict)
            except Exception as e:
                logger().warning(f"Error in adding source and timestamp: {e}")
                logger().debug(e.with_traceback())
        if new_obj_dicts:
            value_list = []
            for obj_dict in new_obj_dicts:
                value_record = []
                for column_name in self.columns.keys():
                    value = obj_dict.get(column_name, None)
                    value_record.append(
                        value
                    )  # TODO next: convert value to duckdb type. now it is automatically converted to str
                value_list.append(value_record)

            self.duckdb_client.batch_insert_into_table(
                table_name=self.duckdb_table_name,
                column_list=self.columns.keys(),
                values=value_list,
            )
            logger().debug(
                f"Inserted extracted records into {self.duckdb_table_name}: {len(new_obj_dicts)}"
            )
        return new_objs

    def get_records(
        self, filter: Optional[Union[Filter, BaseCondition]] = None
    ) -> List[TypeVar_BaseModel]:
        if filter is not None:
            conditions_str, fields, values = to_duckdb_filter(filter)
            where_clause = f"WHERE {conditions_str}"

            # we assume all the fields in the filter are in the table
            results = self.duckdb_client.fetch_all_from_table(
                table_name=self.duckdb_table_name,
                value_list=values,
                where_clause=where_clause,
            )
        else:
            results = self.duckdb_client.fetch_all_from_table(
                table_name=self.duckdb_table_name
            )

        records = []
        for result in results:
            record = duckdb_data_to_pydantic_obj(result, self.extended_model_class)
            records.append(record)
        return records

    def delete_records(
        self, filter: Optional[Union[Filter, BaseCondition]] = None
    ) -> None:
        if filter is not None:
            conditions_str, fields, values = to_duckdb_filter(filter)
            where_clause = f"WHERE {conditions_str}"

            self.duckdb_client.delete_from_table(
                table_name=self.duckdb_table_name,
                where_clause=where_clause,
                value_list=values,
            )
        else:
            self.duckdb_client.delete_from_table(table_name=self.duckdb_table_name)
        logger().info(f"Deleted records from {self.duckdb_table_name}")

    def get_actual_model(self) -> Type[TypeVar_BaseModel]:
        return self.extended_model_class
