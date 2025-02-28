import pytest

from leettools.common import exceptions
from leettools.common.models.model_info import ModelInfoManager
from leettools.context_manager import ContextManager
from leettools.eds.usage.token_converter import MILLION, create_token_converter


def test_token_convert_basic():

    from leettools.eds.usage._impl.token_converter_basic import TokenConverterBasic

    context = ContextManager().get_context()
    settings = context.settings
    settings.DEFAULT_TOKEN_CONVERTER = "token_converter_basic"
    token_converter: TokenConverterBasic = create_token_converter(settings)
    price_dict = ModelInfoManager().get_token_map()

    # Test case 1: Valid input
    provider = "openai"
    model = "gpt-4o"
    token_type = "input"
    token_count = 1000000
    expected_result = round(
        (price_dict[provider][model][token_type] / MILLION * token_count)
        / token_converter.internal_token_price
    )
    assert (
        token_converter.convert_to_common_token(
            provider, model, token_type, token_count
        )
        == expected_result
    )

    # Test case 2: Invalid provider
    adhoc_provider = "invalid_provider"
    model = "gpt-4o"
    token_type = "input"
    token_count = 1000000

    # we should use the default value now.
    adhoc_provider_result = token_converter.convert_to_common_token(
        adhoc_provider, model, token_type, token_count
    )
    assert adhoc_provider_result == expected_result

    # Test case 3: Invalid model
    provider = "openai"
    model = "invalid_model"
    token_type = "input"
    token_count = 1000000
    assert token_converter.convert_to_common_token(
        provider, model, token_type, token_count
    ) == token_converter.convert_to_common_token(
        provider, "default", token_type, token_count
    )

    # Test case 4: Invalid token type
    provider = "openai"
    model = "gpt-4o-mini"
    token_type = "invalid_token_type"
    token_count = 1000000

    assert token_converter.convert_to_common_token(
        provider, model, token_type, token_count
    ) == token_converter.convert_to_common_token(provider, model, "input", token_count)

    # Test case 5: Token price is not available
    provider = "openai"
    model = "text-embedding-3-small"
    token_type = "output"
    token_count = 1000000

    assert token_converter.convert_to_common_token(
        provider, model, token_type, token_count
    ) == token_converter.convert_to_common_token(
        provider, "default", "output", token_count
    )
