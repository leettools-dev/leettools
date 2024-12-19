import random

import pytest
from pydantic import BaseModel

from leettools.core.config.config_manager import ConfigManager


class ConfigTest(BaseModel):
    key: str
    value: str


@pytest.fixture
def config_manager():
    return ConfigManager()


def test_add_config_new(config_manager: ConfigManager):
    config = ConfigTest(key="test_key", value="test_value")
    config_manager.add_config("test_config", config)
    assert "test_config" in config_manager.configs
    assert config_manager.configs["test_config"] == config.model_dump()


def test_add_config_existing_same(config_manager: ConfigManager):
    config = ConfigTest(key="test_key", value="test_value")
    config_manager.add_config("test_config", config)
    assert "test_config" in config_manager.configs
    first_config = config_manager.configs["test_config"]

    config_manager.add_config("test_config", config)
    second_config = config_manager.configs["test_config"]
    assert first_config == second_config


def test_add_config_existing_different(config_manager: ConfigManager):
    config1 = ConfigTest(key="test_key", value="test_value")
    config2 = ConfigTest(key="test_key", value="different_value")
    config_manager.add_config("test_config", config1)
    assert "test_config" in config_manager.configs
    first_config = config_manager.configs["test_config"]

    config_manager.add_config("test_config", config2)
    second_config = config_manager.configs["test_config"]
    assert first_config == second_config
    assert second_config["value"] == "test_value"


def test_load_config(config_manager: ConfigManager, tmp_path):
    filename = f"{tmp_path}/test_config_{random.randint(1,1000)}.yaml"

    config = ConfigTest(key="test_key", value="test_value")
    config_manager.add_config("test_config", config)
    config_manager.dump_configs(filename)

    new_config_manager = ConfigManager()
    new_config_manager.load_configs(filename)
    assert new_config_manager.configs == config_manager.configs

    retrieved_config = new_config_manager.get_config("test_config")
    assert retrieved_config["key"] == "test_key"
