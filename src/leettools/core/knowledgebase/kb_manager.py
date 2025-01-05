from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar, List, Optional

from leettools.common.utils import time_utils
from leettools.core.config.performance_configurable import PerformanceConfigurable
from leettools.core.schemas.knowledgebase import KBCreate, KBUpdate, KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings


def get_kb_name_from_query(query: str) -> str:
    # create a timestamp in the format of "YYYYMMDD_HHMMSS"
    now = time_utils.current_datetime()
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    # get the first two words of the query
    query_words = query.split()
    if len(query_words) < 2:
        kb_name = query
    else:
        kb_name = "_".join(query_words[:2])
    if len(kb_name) > 20:
        kb_name = kb_name[:20]
    return f"adhoc_{kb_name}_{timestamp}"


class AbstractKBManager(ABC, PerformanceConfigurable):
    """
    This is the abstract class for the knowledge base manager, which is responsible for
    adding, updating, and deleting knowledge base entries.
    """

    PerfConfigIdStr: ClassVar[str] = "KnowledgeBase"

    @abstractmethod
    def __init__(self, settings: SystemSettings) -> None:
        pass

    @abstractmethod
    def add_kb(self, org: Org, kb_create: KBCreate) -> Optional[KnowledgeBase]:
        """
        Adds a new knowledge base. If the knowledge base with the same name already exists,
        it raises an EntityExistsException.

        Args:
        - org: The organization object.
        - kb_create: The knowledge base create object.

        Returns:
        - Optional[KnowledgeBase]: The knowledge base object.
        """
        pass

    @abstractmethod
    def update_kb(self, org: Org, kb_update: KBUpdate) -> Optional[KnowledgeBase]:
        """
        Updates an existing knowledge base entry.

        Args:
        - org: The organization object.
        - kb_update: The knowledge base update object.

        Returns:
        - Optional[KnowledgeBase]: The updated knowledge base object.
        """
        pass

    @abstractmethod
    def delete_kb_by_name(self, org: Org, kb_name: str) -> bool:
        """
        Deletes a knowledge base entry.

        Args:
        - org: The organization object.
        - kb_name: The name of the knowledge base.

        Returns:
        - bool: True if the knowledge base was deleted successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_kb_by_name(self, org: Org, kb_name: str) -> Optional[KnowledgeBase]:
        """
        Gets a knowledge base entry by its name.
        """
        pass

    @abstractmethod
    def get_kb_by_id(self, org: Org, kb_id: str) -> Optional[KnowledgeBase]:
        """
        Gets a knowledge base entry by its id.

        Args:
        - org: The organization object.
        - kb_id: The id of the knowledge base.

        Returns:
        - Optional[KnowledgeBase]: The knowledge base object.
        """
        pass

    @abstractmethod
    def get_all_kbs_for_org(
        self, org: Org, list_adhoc: Optional[bool] = False
    ) -> List[KnowledgeBase]:
        """
        Gets all knowledge base entries for an organization.

        Args:
        - org: The organization object.
        - list_adhoc: If True, list adhoc knowledge bases as well.

        Returns:
        - List[KnowledgeBase]: A list of knowledge base objects.
        """
        pass

    @abstractmethod
    def update_kb_timestamp(
        self, org: Org, kb: KnowledgeBase
    ) -> Optional[KnowledgeBase]:
        """
        Force updates the timestamp of the knowledge base.

        Args:
        -   org: The organization object.
        -   kb: The knowledge base object.

        Returns:
        -   Optional[KnowledgeBase]: The updated knowledge base object.
        """
        pass


def create_kb_manager(settings: SystemSettings) -> AbstractKBManager:
    """
    Factory function for creating a kb manager.

    Should only use once in the global context.
    """
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="kb_manager",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractKBManager,
        settings=settings,
    )
