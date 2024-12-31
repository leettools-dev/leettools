from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.docsink import DocSink, DocSinkCreate, DocSinkUpdate
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings


class AbstractDocsinkStore(ABC):
    """DocsinkStore is an abstract class for docsink stores."""

    @abstractmethod
    def create_docsink(
        self, org: Org, kb: KnowledgeBase, docsink_create: DocSinkCreate
    ) -> Optional[DocSink]:
        """
        Add a docsink to the store.

        Args:
        - org: The organization.
        - kb: The knowledgebase.
        - docsink_create: The docsink to be added.

        Returns:
        - The added docsink.
        """
        pass

    @abstractmethod
    def delete_docsink(self, org: Org, kb: KnowledgeBase, docsink: DocSink) -> bool:
        """
        Delete a docsink from the store.

        Args:
        - org: The organization.
        - kb: The knowledgebase.
        - docsink: The docsink to be deleted.

        Returns:
        - True if the docsink was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_docsink_by_id(
        self, org: Org, kb: KnowledgeBase, docsink_uuid: str
    ) -> Optional[DocSink]:
        """
        Get a docsink from the store.

        Args:
        - org: The organization.
        - kb: The knowledgebase.
        - docsink_uuid: The uuid of the docsink.

        Returns:
        - The docsink.
        """
        pass

    @abstractmethod
    def get_docsinks_for_kb(self, org: Org, kb: KnowledgeBase) -> List[DocSink]:
        """
        List all docsinks in the knowledgebase.

        Args:
        - org: The organization.
        - kb: The knowledgebase.

        Returns:
        - A list of docsinks.
        """
        pass

    @abstractmethod
    def get_docsinks_for_docsource(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
    ) -> List[DocSink]:
        """
        List all docsinks in the knowledgebase for a docsource.

        Args:
        - org: The organization.
        - kb: The knowledgebase.
        - docsource: The docsource to get docsinks for.

        Returns:
        - A list of docsinks.
        """
        pass

    @abstractmethod
    def update_docsink(
        self, org: Org, kb: KnowledgeBase, docsink_update: DocSinkUpdate
    ) -> Optional[DocSink]:
        """
        Update a docsink in the store.

        Args:
        - org: The organization.
        - kb: The knowledgebase.
        - docsink_update: The docsink to be updated.

        Returns:
        - The updated docsink.
        """
        pass


def create_docsink_store(settings: SystemSettings) -> AbstractDocsinkStore:
    """
    Creates a new knowledgebase manager.

    Should only use once in the global context.
    """
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="docsink_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractDocsinkStore,
        settings=settings,
    )
