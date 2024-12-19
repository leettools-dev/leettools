import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from leettools.chat.schemas.chat_history import ChatHistory, CHCreate, CHUpdate
from leettools.common.logging import EventLogger
from leettools.common.singleton_meta import SingletonMeta
from leettools.context_manager import Context
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem, ChatQueryItemCreate
from leettools.core.schemas.chat_query_options import ChatQueryOptions
from leettools.core.schemas.chat_query_result import (
    ChatAnswerItemCreate,
    ChatQueryResult,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy import Strategy


class AbstractHistoryManager(ABC):
    """
    This is the abstract class for the chat manager, which is responsible for
    adding, updating, and deleting chat history entries.
    """

    @abstractmethod
    def add_ch_entry(self, ch_create: CHCreate) -> ChatHistory:
        """
        Adds a new chat history entry.
        """
        pass

    @abstractmethod
    def update_ch_entry(self, ch_update: CHUpdate) -> Optional[ChatHistory]:
        """
        Updates an existing chat history entry.
        """
        pass

    @abstractmethod
    def update_ch_entry_answer(
        self,
        username: str,
        chat_id: str,
        query_id: str,
        position_in_answer: str,
        new_answer: ChatAnswerItemCreate,
    ) -> Optional[ChatHistory]:
        """
        Updates an existing chat with a new answer section.

         The old section will have (tmp solution):
            - score=-2 to indicate that it is replaced
            - query_id="-{query_id}-" so that query_id based search will not use it
            - updated updated_at timestamp

        The answer plan for the new section will be set to None to indicate that
        it is manually created.

        Args:
        - username: The username of the chat history entry.
        - chat_id: The chat ID of the chat history entry.
        - query_id: The query ID of the chat history entry.
        - position_in_answer: The position in the answer to update.
        - new_answer: The new answer to update with.

        Returns:
        The updated chat history entry.
        """
        pass

    @abstractmethod
    def add_query_item_to_chat(
        self,
        username: str,
        chat_query_item_create: ChatQueryItemCreate,
        chat_query_options: ChatQueryOptions,
        strategy: Strategy,
    ) -> ChatQueryItem:
        """
        Adds a new query to the chat history entry with the given strategy.

        This function only adds the query to the chat history entry. It does not
        execute the query or add results.

        Args:
        - username: The username of the chat history entry.
        - chat_query_item_create: The query to add.
        - chat_query_options: The options for the query.
        - strategy: The strategy to use for the query.

        Returns:
        - The newly created chat query item.
        """
        pass

    @abstractmethod
    def add_answer_item_to_chat(
        self,
        username: str,
        chat_id: str,
        query_id: str,
        position_in_answer: str,
        new_answer: ChatAnswerItemCreate,
    ) -> ChatHistory:
        """
        Adds a new answer item to the chat history entry at position_in_answer. All
        answer items after position_in_answer will be shifted down by one.

        Args:
        - username: The username of the chat history entry.
        - chat_id: The chat ID of the chat history entry.
        - query_id: The query ID of the chat history entry.
        - position_in_answer: The position in the answer to add the new answer item.
        - new_answer: The new answer to add.

        Returns:
        The updated chat history entry.
        """
        pass

    @abstractmethod
    def remove_answer_item_from_chat(
        self,
        username: str,
        chat_id: str,
        query_id: str,
        position_in_answer: str,
    ) -> Optional[ChatHistory]:
        """
        Removes an answer item from the chat history entry at position_in_answer. All
        answer items after position_in_answer will be shifted up by one.

        Args:
        - username: The username of the chat history entry.
        - chat_id: The chat ID of the chat history entry.
        - query_id: The query ID of the chat history entry.
        - position_in_answer: The position in the answer to remove the answer item from.

        Returns:
        The updated chat history entry.
        """
        pass

    @abstractmethod
    def delete_ch_entry(self, username: str, chat_id: str) -> None:
        """
        Deletes a chat history entry.
        """
        pass

    @abstractmethod
    def delete_ch_entry_item(self, username: str, chat_id: str, query_id: str) -> None:
        """
        Deletes an entry from chat history entry.
        """
        pass

    @abstractmethod
    def get_ch_entry(self, username: str, chat_id: str) -> Optional[ChatHistory]:
        """
        Gets a knowledge base entry by its ID.
        """
        pass

    @abstractmethod
    def get_ch_entries_by_username(self, username: str) -> List[ChatHistory]:
        """
        Gets all knowledge base entries given a username
        """
        pass

    @abstractmethod
    def get_ch_entries_by_username_with_type(
        self, username: str, article_type: str
    ) -> List[ChatHistory]:
        """
        Gets chat history entries with the target type given a username
        """
        pass

    @abstractmethod
    def get_ch_entries_by_username_with_type_in_kb(
        self,
        username: str,
        article_type: Optional[str] = None,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
    ) -> List[ChatHistory]:
        """
        Gets chat history entries with the target type given a username in a kb.

        Args:
        - username: The username to get the chat history entries from.
        - article_type: The article type to filter by. If None, all article types are returned.
        - org: The organization to get the chat history entries from, None means default org.
        - kb: The knowledge base to get the chat history entries from, None if all kbs.

        Returns:
        A list of chat history entries.
        """
        pass

    @abstractmethod
    def get_kb_owner_ch_entries_by_type(
        self, org: Org, kb: KnowledgeBase, article_type: Optional[ArticleType] = None
    ) -> List[ChatHistory]:
        """
        Gets chat history entries from the owner of the KB with the target type given.

        Right now, only the owner of the KB can share articles in the KB. Other users
        can use the KB to create articles and share them, but those articles will not
        show up in the KB sharing list. They will show up in that user's sharing list.

        Args:
        - org: The organization to get the chat history entries from.
        - kb: The knowledge base to get the chat history entries from.
        - article_type: The article type to filter by. If None, all article types are returned.

        Returns:
        A list of chat history entries.
        """
        pass

    @abstractmethod
    def get_shared_samples_by_flow_type(
        self, org: Org, flow_type: str
    ) -> List[ChatHistory]:
        """
        Gets chat history entries with the target flow type given an organization.

        Right now we only return the shared samples from the admin user of the org. Since
        the articles are stored by user, it is expensive to get all the shared articles
        from all the users in the org. Also, it is hard to control the quality of the
        shared articles from all the users in the org. So we only return the shared
        articles from the admin user of the org.

        Args:
        - org: The organization to get the chat history entries from.
        - flow_type: The flow type to filter by.

        Returns:
        - A list of shared chat history entries.
        """
        pass

    @abstractmethod
    def run_query_with_strategy(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item_create: ChatQueryItemCreate,
        chat_query_options: Optional[ChatQueryOptions] = None,
        strategy: Optional[Strategy] = None,
        display_logger: Optional[EventLogger] = None,
    ) -> ChatQueryResult:
        """
        Get answer for the query user provides. If not chat_id is specified in the
        chat_query_item_create, a new chat will be created in the history.

        This function basically prepares the chat_query_item for the query and then
        calls the run_query_item function to get the result.

        Args:
        - org: The organization to run the query on.
        - kb: The knowledge base to run the query on.
        - user: The user to run the query for.
        - chat_query_item_create: The query item to run.
        - chat_query_options: The options for the query, including the flow_options.
        - strategy: The strategy to use for the query, can be a dynamic strategy.
        - display_logger: The logger to log the display messages.

        Returns:
        - The result of the query.
        """
        pass

    @abstractmethod
    def run_query_item(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: Optional[EventLogger] = None,
    ) -> ChatQueryResult:
        """
        This function is similar to the run_query_with_strategy function, but it
        is used to run a query item that is already created in the history manager.

        Args:
        - org: The organization to run the query on.
        - kb: The knowledge base to run the query on.
        - user: The user to run the query for.
        - chat_query_item: The query item to run.
        - display_logger: The logger to log the display messages.

        Returns:
        - The result of the query.
        """
        pass


class _SingletonMetaHM(SingletonMeta):
    _lock: threading.Lock = threading.Lock()


class _HMInstances(metaclass=_SingletonMetaHM):
    """
    This class is used to hold history managers for different store types.

    Should only used in testings.
    """

    def __init__(self):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            self._instances: Dict[str, AbstractHistoryManager] = {}

    def reset_for_test(self):
        with _SingletonMetaHM._lock:
            self._instances = {}

    def get_instance(self, context: Context) -> AbstractHistoryManager:
        with _SingletonMetaHM._lock:
            store_type = context.settings.DOC_STORE_TYPE
            if store_type not in self._instances:
                from leettools.common.utils import factory_util

                hm_instance = factory_util.create_manager_with_repo_type(
                    manager_name="history_manager",
                    repo_type=store_type,
                    base_class=AbstractHistoryManager,
                    context=context,
                )

                self._instances[store_type] = hm_instance
            return self._instances[store_type]


def get_history_manager(context: Context) -> AbstractHistoryManager:
    return _HMInstances().get_instance(context)
