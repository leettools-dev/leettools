from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.strategy.schemas.intention import (
    Intention,
    IntentionCreate,
    IntentionUpdate,
)
from leettools.settings import SystemSettings


class AbstractIntentionStore(ABC):
    """
    Abstract base class for intention stores.

    Intention stores are responsible for storing and retrieving intentions.

    """

    @abstractmethod
    def get_all_intentions(self) -> List[Intention]:
        """
        Get all intentions from the store.
        """
        pass

    @abstractmethod
    def get_intention_by_name(self, intention_name: str) -> Optional[Intention]:
        """
        Get an intention by its name from the store.
        """
        pass

    @abstractmethod
    def create_intention(self, intention_create: IntentionCreate) -> Intention:
        """
        Create an intention in the store.
        """
        pass

    @abstractmethod
    def update_intention(self, intention_update: IntentionUpdate) -> Intention:
        """
        Update an intention in the store.
        """
        pass

    @abstractmethod
    def _reset_for_test(self) -> None:
        """
        Reset the intention store for testing.
        """
        pass


def create_intention_store(settings: SystemSettings) -> AbstractIntentionStore:
    """
    Create a intention store based on the settings.
    """
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="intention_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractIntentionStore,
        settings=settings,
    )
