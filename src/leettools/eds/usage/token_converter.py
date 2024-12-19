from abc import ABC, abstractmethod

from leettools.settings import SystemSettings

MILLION = 1000000


class AbstractTokenConverter(ABC):
    """
    This class converts tokens from different models to a common token.
    """

    @abstractmethod
    def __init__(self, settings: SystemSettings) -> None:
        pass

    @abstractmethod
    def convert_to_common_token(
        self, provider: str, model: str, token_type: str, token_count: int
    ) -> int:
        """
        Convert the token count to the common token.

        Args:
        -   provider (str): The provider name
        -   model (str): The model name
        -   token_type (str): The token type (input, output, batch_input, batch_output)
        -   token_count (int): The token count

        Returns:
        -   int: The price in common token
        """
        pass

    @abstractmethod
    def cents_to_common_token(self, cents: int) -> int:
        """
        Convert the dollar amount in cents to the token count.

        Args:
        -   cents (int): The dollar amount in cents

        Returns:
        -    int: The token count
        """
        pass


def create_token_converter(settings: SystemSettings) -> AbstractTokenConverter:
    # Construct the target module name using the current package
    import os

    from leettools.common.utils import factory_util

    module_name = os.environ.get(SystemSettings.EDS_DEFAULT_TOKEN_CONVERTER)
    if module_name is None or module_name == "":
        module_name = settings.DEFAULT_TOKEN_CONVERTER

    if "." not in module_name:
        module_name = f"{__package__}._impl.{module_name}"

    return factory_util.create_object(
        module_name,
        AbstractTokenConverter,
        settings=settings,
    )
