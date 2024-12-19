from abc import ABC, abstractmethod
from typing import List

from leettools.core.schemas.api_provider_config import APIProviderConfig
from leettools.core.schemas.user import User
from leettools.core.schemas.user_settings import UserSettings, UserSettingsUpdate
from leettools.settings import SystemSettings


class AbstractUserSettingsStore(ABC):

    @abstractmethod
    def get_settings_for_user(self, user: User) -> UserSettings:
        """
        Get the user settings for a user.

        Args:
        user: The user.

        Returns:
        The user settings.
        """
        pass

    @abstractmethod
    def update_settings_for_user(
        self, user: User, settings_update: UserSettingsUpdate
    ) -> UserSettings:
        """
        Update the user settings for a user.

        Args:
        user: The user.
        settings_update: The settings to be updated.

        Returns:
        The updated user settings.
        """
        pass

    @abstractmethod
    def add_api_provider_config(
        self, user: User, api_provider_config: APIProviderConfig
    ) -> APIProviderConfig:
        """
        Add a new API provider config. If a config with the same name exists, it will be updated.

        Args:
        user: The user.
        api_provider_config: The API provider config.

        Returns:
        The API provider config.
        """
        pass

    @abstractmethod
    def get_all_api_provider_configs_for_user(
        self, user: User
    ) -> List[APIProviderConfig]:
        """
        Get all API provider configs for a user.
        """
        pass

    @abstractmethod
    def get_api_provider_config_by_name(
        self, user: User, api_provider_name: str
    ) -> APIProviderConfig:
        """
        Get the api provider config for user by the provider name.
        """
        pass

    @abstractmethod
    def _reset_for_test(self, user_uuid: str) -> None:
        """
        Resets the user settings store for testing purposes.
        """
        pass


def create_user_settings_store(settings: SystemSettings) -> AbstractUserSettingsStore:
    """
    Get the user settings store.

    Args:
    settings: The system settings.

    Returns:
    The user settings store.
    """
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="user_settings_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractUserSettingsStore,
        settings=settings,
    )
