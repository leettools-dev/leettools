from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel

from leettools.common.logging import logger


class ConfigManager:
    """
    Used to record all configs that are used in execution of the program that may
    affect the output of the program. The next program can just load this config
    and reproduce the same output.
    """

    def __init__(self) -> None:
        # the value of the dict is the config's dictionary
        self.configs: Dict[str, Dict[str, Any]] = {}

    def add_config(self, config_name: str, config: BaseModel) -> None:
        """
        Add a config to the manager. If the config with the same name already exists,
        we check if the new config is the same as the existing config. If not, we log
        a warning since we should only store identifiable configs. Basically this is a
        dynamic config file generator.
        """
        new_value = config.model_dump()
        new_value_str = yaml.dump(new_value)
        if config_name in self.configs:
            old_value_str = yaml.dump(self.configs[config_name])
            # check if the two config values are the same by comparing their str values
            if old_value_str != new_value_str:
                # log a warning
                logger().warning(
                    f"Config with name {config_name} already exists, "
                    f"but the new config is different.\n"
                    f"Old config: {old_value_str}\n"
                    f"New config: {new_value_str}"
                )
            return

        self.configs[config_name] = new_value
        return

    def get_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the config by name. If the config does not exist, raise an exception.
        """
        if config_name not in self.configs:
            return None
        return self.configs[config_name]

    def dump_configs(self, output_file: Path) -> None:
        """
        Dump all configs to a file with their names:
        1. write the name of the config as a comment
        2. write the config as a string

        Args:
        - output_file: The file path to dump the configs

        Returns:
        - None
        """
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(self.configs, f)
        return

    def load_configs(self, input_file: Path) -> None:
        """
        Load all configs from a file.

        Args:
        - input_file: The file path to load the configs

        Returns:
        - None
        """
        with open(input_file, "r", encoding="utf-8") as f:
            self.configs = yaml.load(f, Loader=yaml.FullLoader)
        return
