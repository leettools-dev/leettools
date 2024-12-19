from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.context_manager import Context
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.metadata.schemas.kb_metadata import KBMetadata


class AbstractKBMetadataManager(ABC):
    """
    The Metadata for Knowledge Bases such as top domains, keywords, links, and authors.
    """

    @abstractmethod
    def get_kb_metadata(self, org: Org, kb_id: str) -> Optional[KBMetadata]:
        """
        Retrieve the knowledge base (KB) metadata for a given organization and KB ID.

        If there are multiple KB metadata entries for the same KB ID, this method returns
        the one with the latest created_at timestamp.

        Args:
            org (Org): The organization object.
            kb_id (str): The ID of the knowledge base.

        Returns:
            Optional[KBMetadata]: The KB metadata if found, otherwise None.
        """
        pass

    @abstractmethod
    def get_docs_from_domain(
        self, org: Org, kb: KnowledgeBase, top_level_domain: str
    ) -> List[Document]:
        """
        Retrieves a list of documents from a specific top-level domain.

        Args:
            org (Org): The organization.
            kb (KnowledgeBase): The knowledge base.
            top_level_domain (str): The top-level domain to filter the documents.

        Returns:
            List[Document]: A list of documents matching the specified top-level domain.
        """
        pass

    @abstractmethod
    def get_docs_with_keyword(
        self, org: Org, kb: KnowledgeBase, keyword: str
    ) -> List[Document]:
        """
        Retrieves a list of documents with a specific keyword.

        Args:
            org (Org): The organization.
            kb (KnowledgeBase): The knowledge base.
            keyword (str): The keyword to filter the documents.

        Returns:
            List[Document]: A list of documents containing the specified keyword.
        """
        pass

    @abstractmethod
    def get_docs_from_author(
        self, org: Org, kb: KnowledgeBase, author: str
    ) -> List[Document]:
        """
        Retrieves a list of documents from a specific author.

        Args:
            org (Org): The organization.
            kb (KnowledgeBase): The knowledge base.
            author (str): The author to filter the documents.

        Returns:
            List[Document]: A list of documents from the specified author.
        """
        pass


def create_kb_metadata_manager(context: Context) -> AbstractKBMetadataManager:
    from leettools.common.utils import factory_util

    settings = context.settings
    return factory_util.create_manager_with_repo_type(
        manager_name="kb_metadata_manager",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractKBMetadataManager,
        context=context,
    )
