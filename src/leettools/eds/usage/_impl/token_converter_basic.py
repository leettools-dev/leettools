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
            logger().warning(f"Provider {provider} not one of {self.token_map.keys()}")
            provider = "openai"

        if model not in self.token_map[provider]:
            model = "default"

        if token_type not in self.token_map[provider][model]:
            token_type = "input"

        token_price = self.token_map[provider][model][token_type]
        if token_price is None:
            raise exceptions.UnexpectedCaseException(
                unexpecected_case=f"Token price is not available for {provider} {model} {token_type}"
            )
        price_per_token = token_price / MILLION
        total_cost = price_per_token * token_count
        internal_token_count = total_cost / self.internal_token_price
        return round(internal_token_count)

    def cents_to_common_token(self, cents: int) -> int:
        internal_token_count = cents / self.internal_token_price
        return round(internal_token_count)
