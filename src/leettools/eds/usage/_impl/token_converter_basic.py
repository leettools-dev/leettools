from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.models.model_info import ModelInfoManager
from leettools.eds.usage.token_converter import MILLION, AbstractTokenConverter
from leettools.settings import SystemSettings


class TokenConverterBasic(AbstractTokenConverter):

    def __init__(self, settings: SystemSettings) -> None:
        self.settings = settings
        self.token_map = ModelInfoManager().get_token_map()
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
