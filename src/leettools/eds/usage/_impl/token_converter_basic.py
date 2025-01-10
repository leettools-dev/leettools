from typing import Dict, Optional

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.eds.usage.token_converter import MILLION, AbstractTokenConverter
from leettools.settings import SystemSettings


class TokenConverterBasic(AbstractTokenConverter):

    def _load_token_map(self) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
        """
        Load the token map for the different models. Right now it is hardcoded.
        We should read this from a database.

        Returns:
        - Dict[str, Dict[str, Optional[float]]]: The token map
          The first key is the provider name.
          The second key is the model name.
          The the third key is the token type (input, output, batch_input, batch_output)
          The value is the token price in cents, None if not available.
        """
        token_map = {
            "default": {
                "inference": {
                    "input": 50,
                    "output": 150,
                    "batch_input": 25,
                    "batch_output": 75,
                },
                "embed": {
                    "input": 2,
                    "output": None,
                    "batch_input": 1,
                    "batch_output": None,
                },
            },
            "localhost": {
                "default": {
                    "input": 0,
                    "output": 0,
                    "batch_input": 0,
                    "batch_output": 0,
                },
            },
            "openai": {
                "default": {
                    "input": 15,
                    "output": 60,
                    "batch_input": 7.5,
                    "batch_output": 30,
                },
                "gpt-4o-mini": {
                    "input": 15,
                    "output": 60,
                    "batch_input": 7.5,
                    "batch_output": 30,
                },
                "gpt-4o": {
                    "input": 500,
                    "output": 1500,
                    "batch_input": 250,
                    "batch_output": 750,
                },
                "gpt-4o-2024-05-13": {
                    "input": 500,
                    "output": 1500,
                    "batch_input": 250,
                    "batch_output": 750,
                },
                "gpt-3.5-turbo": {
                    "input": 50,
                    "output": 150,
                    "batch_input": 25,
                    "batch_output": 75,
                },
                "text-embedding-3-small": {
                    "input": 2,
                    "output": None,
                    "batch_input": 1,
                    "batch_output": None,
                },
                "text-embedding-3-large": {
                    "input": 13,
                    "output": None,
                    "batch_input": 7,
                    "batch_output": None,
                },
            },
            "claude": {
                "claude-3-5-sonnet": {
                    "input": 300,
                    "output": 1500,
                    "batch_input": None,
                    "batch_output": None,
                },
                "claude-3-5-opus": {
                    "input": 1500,
                    "output": 7500,
                    "batch_input": None,
                    "batch_output": None,
                },
                "claude-3-5-haiku": {
                    "input": 25,
                    "output": 125,
                    "batch_input": None,
                    "batch_output": None,
                },
            },
            "aliyuncs": {
                "qwen-plus": {
                    "input": 50,
                    "output": 150,
                    "batch_input": None,
                    "batch_output": None,
                },
                "text-embedding-v1": {
                    "input": 13,
                    "output": None,
                    "batch_input": 1,
                    "batch_output": None,
                },
                "text-embedding-v2": {
                    "input": 13,
                    "output": None,
                    "batch_input": 7,
                    "batch_output": None,
                },
            },
            "deepseek": {
                "deepseek-v3": {
                    "input": 14,
                    "output": 28,
                    "batch_input": 14,
                    "batch_output": 28,
                },
            },
            "leettools": {
                "default": {
                    "input": 15,
                    "output": 60,
                    "batch_input": 7.5,
                    "batch_output": 30,
                }
            },
        }
        return token_map

    def __init__(self, settings: SystemSettings) -> None:
        self.settings = settings
        self.token_map = self._load_token_map()
        # internal token price is 100 cents per million internal tokens
        self.internal_token_base = 100
        self.internal_token_price = self.internal_token_base / MILLION

    def convert_to_common_token(
        self, provider: str, model: str, token_type: str, token_count: int
    ) -> int:
        if provider not in self.token_map:
            logger().warning(f"Provider not one of {self.token_map.keys()}: {provider}")
            provider = "openai"

        if model not in self.token_map[provider]:
            model = list(self.token_map[provider].keys())[0]

        if token_type not in self.token_map[provider][model]:
            token_type = list(self.token_map[provider][model].keys())[0]

        token_price = self.token_map[provider][model][token_type]
        if token_price is None:
            logger().warning(f"Token price is None for {provider} {model} {token_type}")
            if "default" in self.token_map[provider]:
                token_price = self.token_map[provider]["default"][token_type]
            else:
                raise exceptions.UnexpectedCaseException(
                    f"Token price is None for {provider} {model} {token_type}"
                    " and there is no default model for the provider."
                )

        price_per_token = token_price / MILLION
        total_cost = price_per_token * token_count
        internal_token_count = total_cost / self.internal_token_price
        return round(internal_token_count)

    def cents_to_common_token(self, cents: int) -> int:
        internal_token_count = cents / self.internal_token_price
        return round(internal_token_count)
