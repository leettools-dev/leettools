from abc import ABC, abstractmethod
from typing import List

from leettools.core.strategy.schemas.prompt import (
    Prompt,
    PromptCategory,
    PromptCreate,
    PromptStatus,
    PromptType,
)
from leettools.settings import SystemSettings


class AbstractPromptStore(ABC):
    """
    An abstract class for the prompt store, which stores all the prompts used in the
    system. Right now all prompts are stored in the same collection, but in the future
    we may support multiple collections.
    """

    @abstractmethod
    def create_prompt(self, prompt: PromptCreate) -> Prompt:
        """
        Create a prompt in the store. If the prompt is already in the store, return the
        previously prompt.
        """
        pass

    @abstractmethod
    def get_prompt(self, prompt_id: str) -> Prompt:
        """
        Get a prompt from the store.
        """
        pass

    @abstractmethod
    def set_prompt_status(self, prompt_id: str, status: PromptStatus) -> Prompt:
        """
        Set the status of a prompt in the store.
        """
        pass

    @abstractmethod
    def list_prompts(self) -> List[Prompt]:
        """
        List all the prompts in the store.
        """
        pass

    @abstractmethod
    def list_prompts_by_filter(
        self, category: PromptCategory, type: PromptType, status: PromptStatus
    ) -> List[Prompt]:
        """
        List all the prompts in the store by category and type. If a parameter is None,
        it is not used in the filter.
        """
        pass

    @abstractmethod
    def _reset_for_test(self):
        """
        Reset the collection for testing.
        """
        pass


def create_promptstore(settings: SystemSettings) -> AbstractPromptStore:
    """
    Create a prompt store based on the settings.
    """
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="prompt_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractPromptStore,
        settings=settings,
    )
