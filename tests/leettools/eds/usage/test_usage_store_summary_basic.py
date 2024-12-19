from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.usage.schemas.usage_api_call import (
    API_CALL_ENDPOINT_COMPLETION,
    TokenType,
    UsageAPICallCreate,
)
from leettools.eds.usage.token_converter import create_token_converter


def test_usage_store(tmp_path):
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_function(tmp_path, context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(tmp_path, context: Context, org: Org, kb: KnowledgeBase, user: User):
    from leettools.eds.usage._impl.token_converter_basic import TokenConverterBasic

    settings = context.settings
    settings.DEFAULT_TOKEN_CONVERTER = "token_converter_basic"
    usage_store = context.get_usage_store()

    tc: TokenConverterBasic = create_token_converter(settings)

    api_usage_create_01 = UsageAPICallCreate(
        user_uuid=user.user_uuid,
        api_provider="openai",
        target_model_name="gpt-3.5-turbo",
        endpoint=API_CALL_ENDPOINT_COMPLETION,
        success=True,
        total_token_count=100,
        start_timestamp_in_ms=10000,
        end_timestamp_in_ms=20000,
        system_prompt="test_system_prompt",
        user_prompt="test_user_prompt",
        call_target="test_call_target",
        input_token_count=25,
        output_token_count=75,
    )

    input_count_01 = tc.convert_to_common_token(
        provider="openai", model="gpt-3.5-turbo", token_type="input", token_count=25
    )
    output_count_01 = tc.convert_to_common_token(
        provider="openai", model="gpt-3.5-turbo", token_type="output", token_count=75
    )

    api_usage_record_01 = usage_store.record_api_call(api_usage_create_01)
    assert api_usage_record_01 is not None
    assert api_usage_record_01.usage_record_id is not None
    assert api_usage_record_01.created_at is not None
    assert api_usage_record_01.user_uuid == user.user_uuid
    assert api_usage_record_01.api_provider == "openai"
    assert api_usage_record_01.target_model_name == "gpt-3.5-turbo"
    assert api_usage_record_01.endpoint == API_CALL_ENDPOINT_COMPLETION
    assert api_usage_record_01.success
    assert api_usage_record_01.total_token_count == 100
    assert api_usage_record_01.start_timestamp_in_ms == 10000
    assert api_usage_record_01.end_timestamp_in_ms == 20000
    assert api_usage_record_01.system_prompt == "test_system_prompt"
    assert api_usage_record_01.user_prompt == "test_user_prompt"
    assert api_usage_record_01.call_target == "test_call_target"
    assert api_usage_record_01.input_token_count == 25
    assert api_usage_record_01.output_token_count == 75
    assert api_usage_record_01.input_leet_token_count == input_count_01
    assert api_usage_record_01.output_leet_token_count == output_count_01

    api_usage_create_02 = UsageAPICallCreate(
        user_uuid=user.user_uuid,
        api_provider="openai",
        target_model_name="gpt-4o",
        endpoint=API_CALL_ENDPOINT_COMPLETION,
        success=True,
        total_token_count=200,
        start_timestamp_in_ms=30000,
        end_timestamp_in_ms=40000,
        system_prompt="test_system_prompt",
        user_prompt="test_user_prompt",
        call_target="test_call_target",
        input_token_count=50,
        output_token_count=150,
    )

    input_count_02 = tc.convert_to_common_token(
        provider="openai", model="gpt-4o", token_type="input", token_count=50
    )
    output_count_02 = tc.convert_to_common_token(
        provider="openai", model="gpt-4o", token_type="output", token_count=150
    )

    api_usage_record_02 = usage_store.record_api_call(api_usage_create_02)
    assert api_usage_record_02.usage_record_id is not None
    assert api_usage_record_02.usage_record_id != api_usage_record_01.usage_record_id
    assert api_usage_record_02.input_leet_token_count == input_count_02
    assert api_usage_record_02.output_leet_token_count == output_count_02

    usage_summary = usage_store.get_usage_summary_by_user(
        user_uuid=user.user_uuid,
        start_time_in_ms=0,
        end_time_in_ms=50000,
    )

    assert usage_summary is not None

    print(usage_summary.model_dump_json(indent=2))

    assert usage_summary.token_by_type[TokenType.INPUT] == 75
    assert usage_summary.token_by_type[TokenType.OUTPUT] == 225
    assert (
        usage_summary.leet_token_by_type[TokenType.INPUT]
        == input_count_01 + input_count_02
    )
    assert (
        usage_summary.leet_token_by_type[TokenType.OUTPUT]
        == output_count_01 + output_count_02
    )

    assert len(usage_summary.usage_by_provider) == 1
    provider_summary = usage_summary.usage_by_provider["openai"]
    assert provider_summary.token_by_type[TokenType.INPUT] == 75
    assert provider_summary.token_by_type[TokenType.OUTPUT] == 225

    assert len(provider_summary.usage_by_model) == 2
    model_summary_3 = provider_summary.usage_by_model["gpt-3.5-turbo"]
    assert model_summary_3.token_by_type[TokenType.INPUT] == 25
    assert model_summary_3.token_by_type[TokenType.OUTPUT] == 75
    token_by_endpoint = model_summary_3.token_by_endpoint["completion"]
    assert token_by_endpoint[TokenType.INPUT] == 25
    assert token_by_endpoint[TokenType.OUTPUT] == 75

    model_summary_4 = provider_summary.usage_by_model["gpt-4o"]
    assert model_summary_4.token_by_type[TokenType.INPUT] == 50
    assert model_summary_4.token_by_type[TokenType.OUTPUT] == 150
    token_by_endpoint = model_summary_4.token_by_endpoint["completion"]
    assert token_by_endpoint[TokenType.INPUT] == 50
    assert token_by_endpoint[TokenType.OUTPUT] == 150

    usage_summary = usage_store.get_usage_summary_by_user(
        user_uuid=user.user_uuid,
        start_time_in_ms=0,
        end_time_in_ms=50000,
        start=1,
        limit=1,
    )

    print(usage_summary.model_dump_json(indent=2))
    assert usage_summary.token_by_type[TokenType.INPUT] == 50
    assert usage_summary.token_by_type[TokenType.OUTPUT] == 150
    assert usage_summary.leet_token_by_type[TokenType.INPUT] == input_count_02
    assert usage_summary.leet_token_by_type[TokenType.OUTPUT] == output_count_02

    assert len(usage_summary.usage_by_provider) == 1
    provider_summary = usage_summary.usage_by_provider["openai"]
    assert provider_summary.token_by_type[TokenType.INPUT] == 50
    assert provider_summary.token_by_type[TokenType.OUTPUT] == 150

    assert len(provider_summary.usage_by_model) == 1

    model_summary_4 = provider_summary.usage_by_model["gpt-4o"]
    assert model_summary_4.token_by_type[TokenType.INPUT] == 50
    assert model_summary_4.token_by_type[TokenType.OUTPUT] == 150
    token_by_endpoint = model_summary_4.token_by_endpoint["completion"]
    assert token_by_endpoint[TokenType.INPUT] == 50
    assert token_by_endpoint[TokenType.OUTPUT] == 150
