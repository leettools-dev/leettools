from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.user import User
from leettools.core.strategy.intention_store import AbstractIntentionStore
from leettools.core.strategy.prompt_store import AbstractPromptStore
from leettools.core.strategy.schemas.strategy import Strategy, StrategyCreate
from leettools.core.strategy.schemas.strategy_status import StrategyStatus
from leettools.core.user.user_store import AbstractUserStore
from leettools.settings import SystemSettings


class AbstractStrategyStore(ABC):
    """
    An abstract class for the strategy store, which stores the predefined strategies.

    We want to persist the strategies so that they can be reused across different sessions.
    """

    @abstractmethod
    def get_default_strategy(self) -> Strategy:
        """
        Get the default strategy from the store.
        """
        pass

    @abstractmethod
    def create_strategy_from_path(self, path_str: str, user: User) -> Strategy:
        """
        Create a strategy from a path that contains all the information
        """

    @abstractmethod
    def create_strategy(self, strategy_create: StrategyCreate, user: User) -> Strategy:
        """
        Create a strategy in the store for the user. If no user is specified, the
        strategy will be created in the common database.
        """
        pass

    @abstractmethod
    def get_strategy_by_id(self, strategy_id: str) -> Optional[Strategy]:
        """
        Get a strategy from the store by id.
        """
        pass

    @abstractmethod
    def get_active_strategy_by_name(
        self, strategy_name: str, user: User
    ) -> Optional[Strategy]:
        """
        Get a strategy from the store by name.
        """
        pass

    @abstractmethod
    def set_strategy_status_by_id(
        self, strategy_id: str, status: StrategyStatus
    ) -> Strategy:
        """
        Set the status of a strategy in the store.
        """
        pass

    @abstractmethod
    def list_active_strategies_for_user(self, user: User) -> List[Strategy]:
        """
        List all the strategys for the specified user.
        """
        pass

    @abstractmethod
    def _reset_for_test(self):
        """
        Test only, delete all strategies in the store.
        """
        pass


def create_strategy_store(
    settings: SystemSettings,
    prompt_store: AbstractPromptStore,
    intention_store: AbstractIntentionStore,
    user_store: AbstractUserStore,
    run_init: bool = True,
) -> AbstractStrategyStore:
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="strategy_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractStrategyStore,
        settings=settings,
        prompt_store=prompt_store,
        intention_store=intention_store,
        user_store=user_store,
        run_init=run_init,
    )
