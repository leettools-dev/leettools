from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.schemas.docsource import DocSource, DocSourceCreate, DocSourceUpdate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings


class AbstractDocsourceStore(ABC):

    @abstractmethod
    def create_docsource(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource_create: DocSourceCreate,
        init_status: DocSourceStatus = DocSourceStatus.CREATED,
    ) -> Optional[DocSource]:
        """
        Add a docsource to the store. If the docsource already exists, it will be updated.

        We can set the initial status of the docsource so that the system scheduler
        can pick it up or ignore it. The default status is CREATED so that the scheduler
        can pick it up.

        Args:
        org: The organization.
        kb: The knowledgebase.
        docsource_create: The docsource to be added.
        init_status: The initial status of the docsource, default CREATED.

        Returns:
        The added docsource.
        """
        pass

    @abstractmethod
    def delete_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> bool:
        """
        Delete a docsource from the store.

        Args:
        docsource: The docsource to be deleted.

        Returns:
        True if the docsource was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_docsource(
        self, org: Org, kb: KnowledgeBase, docsource_uuid: str
    ) -> Optional[DocSource]:
        """
        Get a docsource from the store.

        Args:
        kb_id: The id of the knowledgebase.
        docsource_uuid: The uuid of the docsource.

        Returns:
        The docsource.
        """
        pass

    @abstractmethod
    def get_docsources_for_kb(self, org: Org, kb: KnowledgeBase) -> List[DocSource]:
        """
        Get all docsources for a knowledgebase.

        Args:
        org: the organization.
        kb: The knowledgebase.

        Returns:
        A list of docsources.
        """
        pass

    @abstractmethod
    def update_docsource(
        self, org: Org, kb: KnowledgeBase, docsource_update: DocSourceUpdate
    ) -> Optional[DocSource]:
        """
        Update a docsource in the store.

        Args:
        docsource_update: The docsource to be updated.

        Returns:
        The updated docsource.
        """
        pass

    @abstractmethod
    def wait_for_docsource(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        timeout_in_secs: Optional[int] = 300,
    ) -> bool:
        """
        Wait for a docsource to finish processing.

        Right now we can only block and do periodic checks. We can add a watcher later.

        Args:
            org: The organization.
            kb: The knowledgebase.
            docsource: The docsource to wait for.
            timeout_in_secs: The timeout in seconds. Default 5 minutes. Use None for no timeout.

        Returns:
            True if the docsource finished processing, False if timed out.
        """
        pass


def create_docsource_store(settings: SystemSettings) -> AbstractDocsourceStore:
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="docsource_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractDocsourceStore,
        settings=settings,
    )
