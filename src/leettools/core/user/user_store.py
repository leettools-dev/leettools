from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.user import User, UserCreate, UserUpdate
from leettools.settings import SystemSettings


class AbstractUserStore(ABC):
    @abstractmethod
    def create_user(self, user_create: UserCreate) -> Optional[User]:
        """
        Creates a new user in the user store. If the username specified in the user_create
        data is already in use, the user creation will update the user data.

        Args:
            user_create (UserCreate): The user creation data.

        Returns:
            Optional[User]: The created user object, or None if the user creation failed.
        """
        pass

    @abstractmethod
    def delete_user_by_id(self, user_uuid: str) -> bool:
        """
        Delete a user from the store.

        Args:
        user_uuid: The id of the user to be deleted.

        Returns:
        True if the user was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_user_by_uuid(self, user_uuid: str) -> Optional[User]:
        """
        Get a user from the store.

        Args:
        user_uuid: The id of the user to be retrieved.

        Returns:
        The user if it exists, None otherwise.
        """
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieves a user object based on the provided email address.

        Args:
            email (str): The email address of the user.

        Returns:
            Optional[User]: The user object if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_user_by_name(self, username: str) -> Optional[User]:
        """
        Retrieves a user object based on the given username.

        Args:
            username (str): The username of the user to retrieve.

        Returns:
            Optional[User]: The user object if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_user_by_auth_uuid(
        self, auth_provider: str, auth_uuid: str
    ) -> Optional[User]:
        """
        Retrieve a user by their authentication UUID.

        Args:
            auth_provider (str): The authentication provider.
            auth_uuid (str): The authentication UUID.

        Returns:
            Optional[User]: The user object if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_users(self) -> List[User]:
        """
        Get all users from the store.

        Returns:
        A list of users.
        """
        pass

    @abstractmethod
    def update_user(self, user_update: UserUpdate) -> Optional[User]:
        """
        Update a user in the store. If the user does not exist, the update will return None.

        Args:
        user_update: The user to be updated.

        Returns:
        The updated user if it exists, None otherwise.
        """
        pass

    @abstractmethod
    def change_user_balance(self, user_uuid: str, balance_change: int) -> User:
        """
        Change the balance of a user.

        If the user_uuis does not exist, an EntityNotFoundException will be raised.

        Positive balance_change will increase the balance, negative will decrease it.

        Args:
        user_uuid: The id of the user.
        balance_change: The amount to change the balance by.

        Returns:
        The updated user.
        """
        pass

    @abstractmethod
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """
        Retrieve a user by their API key.

        Args:
        api_key: The API key.

        Returns:
        The user object if found, None otherwise.
        """
        pass

    @abstractmethod
    def _reset_for_test(self) -> None:
        """
        Resets the user store for testing purposes.
        """
        pass

    @abstractmethod
    def _get_dbname_for_test(self) -> str:
        """
        Returns the name of the database for testing purposes.

        Returns:
        The name of the test database.
        """
        pass


def create_user_store(settings: SystemSettings) -> AbstractUserStore:
    """
    Create a user store based on the settings.

    Args:
    settings: The system settings.

    Returns:
    The user store.
    """
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="user_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractUserStore,
        settings=settings,
    )
