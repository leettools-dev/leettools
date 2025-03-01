""""
| Model                      | Input   | Output   | Batch Input| Batch Output|
|                            | (per 1M)| (per 1M) | (per 1M)   | (per 1M)    |
|----------------------------|---------|----------|------------|-------------|
| **gpt-4o-mini**            | $0.15   | $0.60    | $0.075     | $0.30       |
| **gpt-4o-mini-2024-07-18** | $0.15   | $0.60    | $0.075     | $0.30       |
| **gpt-4o**                 | $5.00   | $15.00   | $2.50      | $7.50       |
| **gpt-4o-2024-05-13**      | $5.00   | $15.00   | $2.50      | $7.50       |
| **gpt-3.5-turbo**          | $0.50   | $1.50    | $0.25      | $0.75       |
| **text-embedding-3-small** | $0.02   | N/A      | $0.01      | N/A         |
| **text-embedding-3-large** | $0.13   | N/A      | $0.07      | N/A         |
| **claude-3-5-sonnet**      | $3.00   | $15.00   | N/A        | N/A         |
| **claude-3-5-opus**        | $15.00  | $75.00   | N/A        | N/A         |
| **claude-3-5-haiku**       | $0.25   | $1.25    | N/A        | N/A         |
"""

"""
Only claude-3-5-sonnet is available as of 07/10/2024. The other two models will come
later in the year.
"""

from typing import Dict, Optional

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.eds.usage.token_converter import MILLION, AbstractTokenConverter
from leettools.settings import SystemSettings


class TokenConverterLTC(AbstractTokenConverter):

    def _load_token_map(self) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
        """
        Load the token map for the different models. Right now it is hardcoded.
        We should read this from a database.

        Returns:
            Dict[str, Dict[str, Optional[float]]]: The token map
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
                "gpt-4o-mini": {
                    "input": 15,
                    "output": 60,
                    "batch_input": 7.5,
                    "batch_output": 30,
                },
                "gpt-4o-mini-2024-07-18": {
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
        }
        return token_map

    def __init__(self, settings: SystemSettings) -> None:
        self.settings = settings
        self.token_map = self._load_token_map()
        # each token is roughly the same as a gpt-3.5-turbo input token
        self.leet_token_price = 50 / MILLION
        # print("leet_token_price: {:.7f}".format(self.leet_token_price))
        self.leet_token_margin = 0.2

    def convert_to_common_token(
        self, provider: str, model: str, token_type: str, token_count: int
    ) -> int:
        if provider not in self.token_map:
            logger().warning(f"Provider {provider} not one of {self.token_map.keys()}")
            provider = "openai"

        if model not in self.token_map[provider]:
            raise exceptions.InvalidValueException(
                name="model",
                expected="one of {}".format(self.token_map[provider].keys()),
                actual=model,
            )

        if token_type not in self.token_map[provider][model]:
            raise exceptions.InvalidValueException(
                name="token_type",
                expected="one of {}".format(self.token_map[provider][model].keys()),
                actual=token_type,
            )

        token_price = self.token_map[provider][model][token_type]
        if token_price is None:
            raise exceptions.UnexpectedCaseException(
                unexpecected_case=f"Token price is not available for {provider} {model} {token_type}"
            )
        price_per_token = token_price / MILLION
        total_price = price_per_token * token_count
        leet_token_count = (total_price / self.leet_token_price) * (
            1 + self.leet_token_margin
        )
        return round(leet_token_count)

    def cents_to_common_token(self, cents: int) -> int:
        leet_token_count = cents / self.leet_token_price
        return round(leet_token_count)
