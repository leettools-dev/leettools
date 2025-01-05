import uuid
from datetime import datetime
from typing import List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.utils import time_utils
from leettools.core.user.user_store import AbstractUserStore
from leettools.eds.usage._impl.duckdb.usage_store_duckdb_schema import (
    UsageAPICallDuckDBSchema,
)
from leettools.eds.usage.schemas.usage_api_call import (
    TokenType,
    UsageAPICall,
    UsageAPICallCreate,
    UsageAPICallSummary,
    UsageAPIProviderSummary,
    UsageModelSummary,
)
from leettools.eds.usage.token_converter import create_token_converter
from leettools.eds.usage.usage_store import AbstractUsageStore
from leettools.settings import SystemSettings

USAGE_API_CALL = "api_call"


class UsageStoreDuckDB(AbstractUsageStore):

    def __init__(self, settings: SystemSettings, user_store: AbstractUserStore) -> None:

        self.settings = settings
        self.token_converter = create_token_converter(settings)
        self.user_store = user_store
        self.duckdb_client = DuckDBClient(self.settings)

    def _get_table_name(self, usage_type: str) -> str:
        return self.duckdb_client.create_table_if_not_exists(
            self.settings.DB_USAGE,
            usage_type,
            UsageAPICallDuckDBSchema.get_schema(),
        )

    def record_api_call(self, api_usage_create: UsageAPICallCreate) -> UsageAPICall:
        table_name = self._get_table_name(USAGE_API_CALL)

        data_dict = api_usage_create.model_dump()
        data_dict["created_at"] = time_utils.current_datetime()

        # convert the usage to LeetToken
        if (
            api_usage_create.input_token_count != None
            and api_usage_create.input_token_count > 0
        ):
            input_leet_token = self.token_converter.convert_to_common_token(
                provider=api_usage_create.api_provider,
                model=api_usage_create.target_model_name,
                token_type="input",
                token_count=api_usage_create.input_token_count,
            )
        else:
            input_leet_token = 0
        data_dict["input_leet_token_count"] = input_leet_token

        if (
            api_usage_create.output_token_count != None
            and api_usage_create.output_token_count > 0
        ):
            output_leet_token = self.token_converter.convert_to_common_token(
                provider=api_usage_create.api_provider,
                model=api_usage_create.target_model_name,
                token_type="output",
                token_count=api_usage_create.output_token_count,
            )
        else:
            output_leet_token = 0
        data_dict["output_leet_token_count"] = output_leet_token
        data_dict["usage_record_id"] = str(uuid.uuid4())
        column_list = list(data_dict.keys())
        value_list = list(data_dict.values())
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )
        usage_api_call = UsageAPICall.model_validate(data_dict)

        # update the balance
        # TODO: We need to add a lock for duckdb implementation
        self.user_store.change_user_balance(
            user_uuid=api_usage_create.user_uuid,
            balance_change=-1 * (input_leet_token + output_leet_token),
        )
        return usage_api_call

    def get_usage_summary_by_user(
        self,
        user_uuid: str,
        start_time_in_ms: int,
        end_time_in_ms: int,
        start: Optional[int] = 0,
        limit: Optional[int] = 0,
    ) -> UsageAPICallSummary:
        table_name = self._get_table_name(USAGE_API_CALL)

        where_clause = (
            f"WHERE {UsageAPICall.FIELD_USER_UUID} = ? AND "
            f"{UsageAPICall.FIELD_END_TIMESTAMP_IN_MS} > ? AND "
            f"{UsageAPICall.FIELD_END_TIMESTAMP_IN_MS} <= ?"
        )
        value_list = [user_uuid, start_time_in_ms, end_time_in_ms]
        if limit > 0 and start > 0:
            where_clause += f" LIMIT ? OFFSET ?"
            value_list += [limit, start]
        elif start > 0:
            where_clause += f" OFFSET ?"
            value_list += [start]

        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        usage_summary = UsageAPICallSummary(
            token_by_type={key: 0 for key in TokenType},
            leet_token_by_type={key: 0 for key in TokenType},
            usage_by_provider={},
        )

        for rtn_dict in rtn_dicts:
            record = UsageAPICall.model_validate(rtn_dict)

            provider = record.api_provider
            if provider not in usage_summary.usage_by_provider:
                usage_summary.usage_by_provider[provider] = UsageAPIProviderSummary(
                    token_by_type={key: 0 for key in TokenType},
                    leet_token_by_type={key: 0 for key in TokenType},
                    usage_by_model={},
                )

            cur_provider = usage_summary.usage_by_provider[provider]

            target_model_name = record.target_model_name
            if target_model_name not in cur_provider.usage_by_model:
                cur_provider.usage_by_model[target_model_name] = UsageModelSummary(
                    token_by_type={key: 0 for key in TokenType},
                    leet_token_by_type={key: 0 for key in TokenType},
                    token_by_endpoint={},
                    leet_token_by_endpoint={},
                )
            cur_model = cur_provider.usage_by_model[target_model_name]

            endpoint = record.endpoint
            if endpoint == None or endpoint == "":
                endpoint = "default"

            token_count_input = record.input_token_count
            token_count_output = record.output_token_count
            lt_count_input = record.input_leet_token_count
            lt_count_output = record.output_leet_token_count

            if endpoint in cur_model.token_by_endpoint:
                cur_endpoint = cur_model.token_by_endpoint[endpoint]
                cur_endpoint[TokenType.INPUT] += token_count_input
                cur_endpoint[TokenType.OUTPUT] += token_count_output

                cur_endpoint_leet = cur_model.leet_token_by_endpoint[endpoint]
                cur_endpoint_leet[TokenType.INPUT] += lt_count_input
                cur_endpoint_leet[TokenType.OUTPUT] += lt_count_output
            else:
                cur_model.token_by_endpoint[endpoint] = {
                    TokenType.INPUT: token_count_input,
                    TokenType.OUTPUT: token_count_output,
                }
                cur_model.leet_token_by_endpoint[endpoint] = {
                    TokenType.INPUT: lt_count_input,
                    TokenType.OUTPUT: lt_count_output,
                }

            cur_model.token_by_type[TokenType.INPUT] += token_count_input
            cur_model.token_by_type[TokenType.OUTPUT] += token_count_output
            cur_model.leet_token_by_type[TokenType.INPUT] += lt_count_input
            cur_model.leet_token_by_type[TokenType.OUTPUT] += lt_count_output

            cur_provider.token_by_type[TokenType.INPUT] += token_count_input
            cur_provider.token_by_type[TokenType.OUTPUT] += token_count_output
            cur_provider.leet_token_by_type[TokenType.INPUT] += lt_count_input
            cur_provider.leet_token_by_type[TokenType.OUTPUT] += lt_count_output

            usage_summary.token_by_type[TokenType.INPUT] += token_count_input
            usage_summary.token_by_type[TokenType.OUTPUT] += token_count_output
            usage_summary.leet_token_by_type[TokenType.INPUT] += lt_count_input
            usage_summary.leet_token_by_type[TokenType.OUTPUT] += lt_count_output

        return usage_summary

    def get_api_usage_count_by_user(
        self,
        user_uuid: str,
        start_time_in_ms: int,
        end_time_in_ms: int,
    ) -> int:
        table_name = self._get_table_name(USAGE_API_CALL)

        where_clause = (
            f"WHERE {UsageAPICall.FIELD_USER_UUID} = ? AND "
            f"{UsageAPICall.FIELD_END_TIMESTAMP_IN_MS} > ? AND "
            f"{UsageAPICall.FIELD_END_TIMESTAMP_IN_MS} <= ?"
        )
        column_list = ["COUNT(*) as count"]
        value_list = [user_uuid, start_time_in_ms, end_time_in_ms]
        rtn = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
            column_list=column_list,
        )
        if rtn is None:
            return 0
        else:
            return rtn["count"]

    def get_api_usage_details_by_user(
        self,
        user_uuid: str,
        start_time_in_ms: int,
        end_time_in_ms: int,
        start: Optional[int] = 0,
        limit: Optional[int] = 0,
    ) -> List[UsageAPICall]:
        table_name = self._get_table_name(USAGE_API_CALL)

        where_clause = (
            f"WHERE {UsageAPICall.FIELD_USER_UUID} = ? AND "
            f"{UsageAPICall.FIELD_END_TIMESTAMP_IN_MS} > ? AND "
            f"{UsageAPICall.FIELD_END_TIMESTAMP_IN_MS} <= ?"
        )
        value_list = [user_uuid, start_time_in_ms, end_time_in_ms]
        if limit > 0 and start >= 0:
            where_clause += f" LIMIT ? OFFSET ?"
            value_list += [limit, start]
        elif start > 0:
            where_clause += f" OFFSET ?"
            value_list += [start]

        rtn_dicts = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        rtn_list = []

        for rtn_dict in rtn_dicts:
            usage_api_call = UsageAPICall.model_validate(rtn_dict)
            usage_api_call.user_prompt = None
            usage_api_call.system_prompt = None
            rtn_list.append(usage_api_call)

        return rtn_list

    def get_api_usage_detail_by_id(
        self, usage_record_id: str
    ) -> Optional[UsageAPICall]:
        table_name = self._get_table_name(USAGE_API_CALL)

        where_clause = f"WHERE {UsageAPICall.FIELD_USAGE_RECORD_ID} = ?"
        value_list = [usage_record_id]
        rtn_dict = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        if rtn_dict is None:
            return None
        return UsageAPICall.model_validate(rtn_dict)
