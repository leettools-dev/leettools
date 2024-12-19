from leettools.common.temp_setup import TempSetup
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.usage.schemas.usage_api_call import (
    API_CALL_ENDPOINT_COMPLETION,
    UsageAPICallCreate,
)


def test_usage_store(tmp_path):

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(tmp_path, context, org, kb, user)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(tmp_path, context: Context, org: Org, kb: KnowledgeBase, user: User):

    usage_store = context.get_usage_store()

    api_usage_create_01 = UsageAPICallCreate(
        user_uuid=user.user_uuid,
        api_provider="test_provider_x",
        target_model_name="test_model_01",
        endpoint=API_CALL_ENDPOINT_COMPLETION,
        success=True,
        total_token_count=100,
        start_timestamp_in_ms=10000,
        end_timestamp_in_ms=20000,
        system_prompt="test_system_prompt",
        user_prompt="test_user_prompt",
        call_target="test_call_target",
    )

    api_usage_record_01 = usage_store.record_api_call(api_usage_create_01)
    assert api_usage_record_01 is not None
    assert api_usage_record_01.usage_record_id is not None
    assert api_usage_record_01.created_at is not None
    assert api_usage_record_01.user_uuid == user.user_uuid
    assert api_usage_record_01.api_provider == "test_provider_x"
    assert api_usage_record_01.target_model_name == "test_model_01"
    assert api_usage_record_01.endpoint == API_CALL_ENDPOINT_COMPLETION
    assert api_usage_record_01.success
    assert api_usage_record_01.total_token_count == 100
    assert api_usage_record_01.start_timestamp_in_ms == 10000
    assert api_usage_record_01.end_timestamp_in_ms == 20000
    assert api_usage_record_01.system_prompt == "test_system_prompt"
    assert api_usage_record_01.user_prompt == "test_user_prompt"
    assert api_usage_record_01.call_target == "test_call_target"

    api_usage_create_02 = UsageAPICallCreate(
        user_uuid=user.user_uuid,
        api_provider="test_provider_x",
        target_model_name="test_model_02",
        endpoint=API_CALL_ENDPOINT_COMPLETION,
        success=True,
        total_token_count=200,
        start_timestamp_in_ms=30000,
        end_timestamp_in_ms=40000,
        system_prompt="test_system_prompt",
        user_prompt="test_user_prompt",
        call_target="test_call_target",
    )

    api_usage_record_02 = usage_store.record_api_call(api_usage_create_02)
    assert api_usage_record_02.usage_record_id is not None
    assert api_usage_record_02.usage_record_id != api_usage_record_01.usage_record_id

    api_usage_record_retrieved = usage_store.get_api_usage_detail_by_id(
        api_usage_record_01.usage_record_id
    )
    assert api_usage_record_retrieved is not None
    assert (
        api_usage_record_retrieved.usage_record_id
        == api_usage_record_01.usage_record_id
    )
    assert api_usage_record_retrieved.user_uuid == user.user_uuid
    assert api_usage_record_retrieved.api_provider == "test_provider_x"
    assert api_usage_record_retrieved.target_model_name == "test_model_01"
    assert api_usage_record_retrieved.endpoint == API_CALL_ENDPOINT_COMPLETION
    assert api_usage_record_retrieved.success
    assert api_usage_record_retrieved.total_token_count == 100
    assert api_usage_record_retrieved.start_timestamp_in_ms == 10000
    assert api_usage_record_retrieved.end_timestamp_in_ms == 20000
    assert api_usage_record_retrieved.system_prompt == "test_system_prompt"
    assert api_usage_record_retrieved.user_prompt == "test_user_prompt"
    assert api_usage_record_retrieved.call_target == "test_call_target"

    fake_id = "1234567890abcdef12345678"
    assert usage_store.get_api_usage_detail_by_id(fake_id) is None

    record_count = usage_store.get_api_usage_count_by_user(
        user_uuid=user.user_uuid,
        start_time_in_ms=0,
        end_time_in_ms=time_utils.cur_timestamp_in_ms(),
    )
    assert record_count == 2

    list_of_usage_records = usage_store.get_api_usage_details_by_user(
        user_uuid=user.user_uuid,
        start_time_in_ms=0,
        end_time_in_ms=time_utils.cur_timestamp_in_ms(),
    )
    assert len(list_of_usage_records) == 2

    list_of_usage_records = usage_store.get_api_usage_details_by_user(
        user_uuid=user.user_uuid,
        start_time_in_ms=0,
        end_time_in_ms=time_utils.cur_timestamp_in_ms(),
        start=0,
        limit=1,
    )
    assert len(list_of_usage_records) == 1

    list_of_usage_records = usage_store.get_api_usage_details_by_user(
        user_uuid=user.user_uuid,
        start_time_in_ms=0,
        end_time_in_ms=time_utils.cur_timestamp_in_ms(),
        start=1,
        limit=0,
    )
    assert len(list_of_usage_records) == 1
