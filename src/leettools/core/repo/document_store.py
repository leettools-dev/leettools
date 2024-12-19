from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document, DocumentCreate, DocumentUpdate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings


class AbstractDocumentStore(ABC):
    """DocumentStore is an abstract class for document stores."""

    @abstractmethod
    def create_document(
        self, org: Org, kb: KnowledgeBase, document_create: DocumentCreate
    ) -> Optional[Document]:
        """
        Create a new document in the store.

        Args:
        org: The organization.
        kb: The knowledgebase.
        document_create: The document to be created.

        Returns:
        The created document.
        """
        pass

    @abstractmethod
    def delete_document(self, org: Org, kb: KnowledgeBase, document: Document) -> bool:
        """
        Delete a document from the store.

        Args:
        org: The organization.
        kb: The knowledgebase.
        document: The document to be deleted.

        Returns:
        True if the document was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_document_by_id(
        self, org: Org, kb: KnowledgeBase, document_uuid: str
    ) -> Optional[Document]:
        """
        Get a document from the store.

        Args:
        org: The organization.
        kb: The knowledgebase.
        document_uuid: The uuid of the document.

        Returns:
        The document with the given doc_uri.
        """
        pass

    @abstractmethod
    def get_documents_for_kb(self, org: Org, kb: KnowledgeBase) -> List[Document]:
        """
        Get all documents for a knowledgebase.

        Args:
        org: The organization.
        kb: The knowledgebase.

        Returns:
        A list of all documents in the knowledgebase.
        """
        pass

    @abstractmethod
    def get_documents_for_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[Document]:
        """
        Get all documents from the store for this docsource.

        Args:
        org: The organization.
        kb: The knowledgebase.
        docsource: The docsource to get documents for.

        Returns:
        A list of all documents for the docsource.
        """
        pass

    @abstractmethod
    def get_document_ids_for_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[str]:
        """
        Get all document ids from the store for a docsource.

        Args:
        org: The organization.
        kb: The knowledgebase.
        docsource: The docsource to get documents for.

        Returns:
        A list of all document ids for the docsource.
        """
        pass

    @abstractmethod
    def get_documents_for_docsink(
        self, org: Org, kb: KnowledgeBase, docsink: DocSink
    ) -> List[Document]:
        """
        Get all documents from the store for this docsink.

        Args:
        org: The organization.
        kb: The knowledgebase.
        docsink: The docsink to get documents for.

        Returns:
        A list of all documents for the docsink.
        """

    @abstractmethod
    def update_document(
        self, org: Org, kb: KnowledgeBase, document_update: DocumentUpdate
    ) -> Optional[Document]:
        """
        Update a document in the store.

        Args:
        document_update: The document to be updated.

        Returns:
        The updated document.
        """
        pass


def create_document_store(settings: SystemSettings) -> AbstractDocumentStore:
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="document_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractDocumentStore,
        settings=settings,
    )
