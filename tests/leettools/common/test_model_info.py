import pytest

from leettools.common.models.model_info import ModelInfo, ModelInfoManager


def test_model_info_dataclass():
    """Test ModelInfo dataclass initialization"""
    token_map = {"provider": {"model": {"input": 1.0}}}
    model_info = ModelInfo(
        provider="test_provider",
        model_name="test_model",
        context_size=1000,
        support_pydantic_response=True,
        support_json_response=True,
        token_map=token_map,
    )

    assert model_info.provider == "test_provider"
    assert model_info.model_name == "test_model"
    assert model_info.context_size == 1000
    assert model_info.support_pydantic_response is True
    assert model_info.support_json_response is True
    assert model_info.token_map == token_map


def test_model_info_manager_singleton():
    """Test ModelInfoManager maintains singleton pattern"""
    manager1 = ModelInfoManager()
    manager2 = ModelInfoManager()
    assert manager1 is manager2


def test_get_context_size():
    """Test context size retrieval for different models"""
    manager = ModelInfoManager()

    # Test known models
    assert manager.get_context_size("gpt-3.5-turbo") == 16385
    assert manager.get_context_size("gpt-4") == 8192
    assert manager.get_context_size("deepseek-chat") == 65536

    # Test unknown model (should return default context size)
    with pytest.warns(None) as record:
        context_size = manager.get_context_size("unknown-model")
    assert context_size > 0  # Should return some default value


def test_support_pydantic_response():
    """Test pydantic response support checking"""
    manager = ModelInfoManager()

    # Test models that should support pydantic
    assert manager.support_pydantic_response("gpt-4")
    assert manager.support_pydantic_response("gpt-3.5-turbo")
    assert manager.support_pydantic_response("o1-mini")

    # Test models that shouldn't support pydantic
    assert not manager.support_pydantic_response("deepseek-chat")
    assert not manager.support_pydantic_response("llama3-8b-8192")


def test_support_json_response():
    """Test JSON response support checking"""
    manager = ModelInfoManager()

    # Test models that should support JSON
    assert manager.support_json_response("gpt-4")
    assert manager.support_json_response("deepseek-chat")
    assert manager.support_json_response("llama3.2")

    # Test models that shouldn't support JSON
    assert not manager.support_json_response("unknown-model")


def test_get_token_map():
    """Test token map retrieval"""
    manager = ModelInfoManager()
    token_map = manager.get_token_map()

    # Check basic structure and some key entries
    assert "default" in token_map
    assert "openai" in token_map
    assert "claude" in token_map

    # Check specific token costs
    assert token_map["openai"]["gpt-3.5-turbo"]["input"] == 50
    assert token_map["openai"]["gpt-3.5-turbo"]["output"] == 150
    assert token_map["claude"]["claude-3-5-sonnet"]["input"] == 300


def test_provider_not_supported():
    """Test provider parameter raises error"""
    manager = ModelInfoManager()

    with pytest.raises(ValueError, match="Provider is not supported yet"):
        manager.get_context_size("gpt-4", provider="openai")

    with pytest.raises(ValueError, match="Provider is not supported yet"):
        manager.support_pydantic_response("gpt-4", provider="openai")

    with pytest.raises(ValueError, match="Provider is not supported yet"):
        manager.support_json_response("gpt-4", provider="openai")
