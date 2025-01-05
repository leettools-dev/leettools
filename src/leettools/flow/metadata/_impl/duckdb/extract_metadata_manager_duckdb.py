import json
from typing import Any, Dict, List

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.flow.metadata._impl.duckdb.extract_metadata_duckdb_schema import (
    DuckDBExtractMetadataSchema,
)
from leettools.flow.metadata.extract_metadata_manager import (
    AbstractExtractMetadataManager,
)
from leettools.flow.schemas.extract_metadata import ExtractMetadata
from leettools.settings import SystemSettings


class ExtractMetadataManagerDuckDB(AbstractExtractMetadataManager):
    """
    ExtractMetadataManagerDuckDB is a ExtractMetadataManager implementation using DuckDB as the backend.
    """

    def __init__(self, settings: SystemSettings) -> None:
        """
        Initialize the DuckDB.
        """
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)

    def _dict_to_extract_metadata(
        self, extract_metadata_dict: Dict[str, Any]
    ) -> ExtractMetadata:
        if ExtractMetadata.FIELD_TARGET_MODEL_SCHEMA_DICT in extract_metadata_dict:
            extract_metadata_dict[ExtractMetadata.FIELD_TARGET_MODEL_SCHEMA_DICT] = (
                json.loads(
                    extract_metadata_dict[
                        ExtractMetadata.FIELD_TARGET_MODEL_SCHEMA_DICT
                    ]
                )
            )
        if ExtractMetadata.FIELD_KEY_FIELDS in extract_metadata_dict:
            key_fields_str = extract_metadata_dict[ExtractMetadata.FIELD_KEY_FIELDS]
            key_fields_str = key_fields_str[1:-1]
            extract_metadata_dict[ExtractMetadata.FIELD_KEY_FIELDS] = (
                key_fields_str.split(",")
            )

        if ExtractMetadata.FIELD_VERIFY_FIELDS in extract_metadata_dict:
            verify_fields_str = extract_metadata_dict[
                ExtractMetadata.FIELD_VERIFY_FIELDS
            ]
            verify_fields_str = verify_fields_str[1:-1]
            extract_metadata_dict[ExtractMetadata.FIELD_VERIFY_FIELDS] = (
                verify_fields_str.split(",")
            )
        return ExtractMetadata.model_validate(extract_metadata_dict)

    def _extract_metadata_to_dict(
        self, extract_metadata: ExtractMetadata
    ) -> Dict[str, Any]:
        extract_metadata_dict = extract_metadata.model_dump()
        if ExtractMetadata.FIELD_KEY_FIELDS in extract_metadata_dict:
            extract_metadata_dict[ExtractMetadata.FIELD_KEY_FIELDS] = (
                "["
                + ",".join(extract_metadata_dict[ExtractMetadata.FIELD_KEY_FIELDS])
                + "]"
            )

        if ExtractMetadata.FIELD_VERIFY_FIELDS in extract_metadata_dict:
            extract_metadata_dict[ExtractMetadata.FIELD_VERIFY_FIELDS] = (
                "["
                + ",".join(extract_metadata_dict[ExtractMetadata.FIELD_VERIFY_FIELDS])
                + "]"
            )
        if ExtractMetadata.FIELD_TARGET_MODEL_SCHEMA_DICT in extract_metadata_dict:
            extract_metadata_dict[ExtractMetadata.FIELD_TARGET_MODEL_SCHEMA_DICT] = (
                json.dumps(
                    extract_metadata_dict[
                        ExtractMetadata.FIELD_TARGET_MODEL_SCHEMA_DICT
                    ]
                )
            )
        return extract_metadata_dict

    def _get_table_name(self, org: Org, kb: KnowledgeBase) -> str:
        org_db_name = Org.get_org_db_name(org.org_id)
        collection_name = kb.collection_name_for_extraction_list()
        return self.duckdb_client.create_table_if_not_exists(
            org_db_name,
            collection_name,
            DuckDBExtractMetadataSchema.get_schema(),
        )

    def add_extracted_db_info(
        self, org: Org, kb: KnowledgeBase, info: ExtractMetadata
    ) -> None:
        table_name = self._get_table_name(org, kb)
        extracted_info = self._extract_metadata_to_dict(info)
        column_list = list(extracted_info.keys())
        value_list = list(extracted_info.values())
        self.duckdb_client.insert_into_table(table_name, column_list, value_list)

    def get_extracted_db_info(
        self, org: Org, kb: KnowledgeBase
    ) -> Dict[str, List[ExtractMetadata]]:
        table_name = self._get_table_name(org, kb)
        rtn_dict: Dict[str, List[ExtractMetadata]] = {}
        # TODO: add filters and deletions
        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
        )
        for info_dict in rtn_dicts:
            info = self._dict_to_extract_metadata(info_dict)
            target_schema_name = info.target_model_name
            if target_schema_name in rtn_dict:
                rtn_dict[target_schema_name].append(info)
            else:
                rtn_dict[target_schema_name] = [info]
        return rtn_dict
