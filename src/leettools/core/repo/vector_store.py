from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.eds.rag.search.filter import Filter


class VectorType(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    COMMON = "common"


class VectorSearchResult(BaseModel):
    segment_uuid: str
    search_score: float
    vector_type: Optional[VectorType] = VectorType.DENSE


class AbstractVectorStore(ABC):

    @abstractmethod
    def __init__(self, context: Context):
        pass

    @abstractmethod
    def save_segments(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        segments: List[Segment],
    ) -> bool:
        """
        Create a segment vector in the store.

        Args:
        - org: The organization to create the segment in.
        - kb: The knowledge base to create the segment in.
        - user: The user to create the segment for.
        - segments: The list of segments to create.

        Returns:
        - True if the segments were saved successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_segment_vector(
        self, org: Org, kb: KnowledgeBase, segment_uuid: str
    ) -> List[Any]:
        """
        Get a segment vector from the store.

        The vector is a list of floats, but may store in a different format.

        Args:
        - org: The organization to get the segment from.
        - kb: The knowledge base to get the segment from.
        - segment_uuid: The segment_uuid to get.

        Returns:
        - The segment vector.
        """
        pass

    @abstractmethod
    def search_in_kb(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        query: str,
        top_k: int,
        search_params: Dict[str, Any] = None,
        filter: Filter = None,
    ) -> List[VectorSearchResult]:
        """
        Search for segments in the store.

        Args:
        - org: The organization to search in.
        - kb: The knowledge base to search in.
        - user: The user to search for.
        - query: The query to search for.
        - top_k: The number of results to return.
        - search_params: The parameters to use for the search.
        - filter: The filter expression to use for the search.

        Returns:
        - A list of segment ids that match the query.
        """
        pass

    @abstractmethod
    def update_segment_vector(
        self, org: Org, kb: KnowledgeBase, user: User, segment: Segment
    ) -> bool:
        """
        Update a segment vectorr in the store.

        Args:
        - org: The organization to update the segment in.
        - kb: The knowledge base to update the segment in.
        - user: The user to update the segment for.
        - segment: The segment to update.

        Returns:
        - True if the segment was updated, False otherwise.
        """
        pass

    @abstractmethod
    def delete_segment_vector(
        self, org: Org, kb: KnowledgeBase, segment_uuid: str
    ) -> bool:
        """
        Delete a segment vector from the store.

        Args:
        - org: The organization to delete the segment from.
        - kb: The knowledge base to delete the segment from.
        - segment_uuid: The segment_uuid to delete.

        Returns:
        - True if the segment was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def delete_segment_vectors_by_document_id(
        self, org: Org, kb: KnowledgeBase, document_uuid: str
    ) -> bool:
        """
        Delete a list of segment vectors from the store by document id.

        Args:
        - org: The organization to delete the segment from.
        - kb: The knowledge base to delete the segment from.
        - document_uuid: The document_uuid to delete.

        Returns:
        - True if the segment was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def delete_segment_vectors_by_docsource_uuid(
        self, org: Org, kb: KnowledgeBase, docsource_uuid: str
    ) -> bool:
        """
        Delete a list of segment vectors from the store by docsource uuid.

        Args:
        - org: The organization to delete the segment from.
        - kb: The knowledge base to delete the segment from.
        - docsource_uuid: The docsource_uuid to delete.

        Returns:
        - True if the segment was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def delete_segment_vectors_by_docsink_uuid(
        self, org: Org, kb: KnowledgeBase, docsink_uuid: str
    ) -> bool:
        """
        Delete a list of segment vectors from the store by docsink uuid.

        Args:
        - org: The organization to delete the segment from.
        - kb: The knowledge base to delete the segment from.
        - docsink_uuid: The docsink_uuid to delete.

        Returns:
        - True if the segment was deleted, False otherwise.
        """
        pass


def create_vector_store_dense(context: Context) -> AbstractVectorStore:
    from leettools.common.utils import factory_util

    settings = context.settings
    return factory_util.create_manager_with_repo_type(
        manager_name="vector_store_dense",
        repo_type=settings.VECTOR_STORE_TYPE,
        base_class=AbstractVectorStore,
        context=context,
    )


def create_vector_store_sparse(context: Context) -> AbstractVectorStore:
    from leettools.common.utils import factory_util

    settings = context.settings
    return factory_util.create_manager_with_repo_type(
        manager_name="vector_store_sparse",
        repo_type=settings.VECTOR_STORE_TYPE,
        base_class=AbstractVectorStore,
        context=context,
    )
