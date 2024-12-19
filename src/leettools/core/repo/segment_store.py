from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import (
    Segment,
    SegmentCreate,
    SegmentInDB,
    SegmentUpdate,
)
from leettools.settings import SystemSettings


class AbstractSegmentStore(ABC):

    @abstractmethod
    def create_segment(
        self, org: Org, kb: KnowledgeBase, segment_create: SegmentCreate
    ) -> Segment:
        """
        Create a new segment in the store.

        Args:
        - org: The organization to create the segment in.
        - kb: The knowledge base to create the segment in.
        - segment_create: The segment to be created.

        Returns:
        - The created segment.
        """
        pass

    @abstractmethod
    def delete_segment(self, org: Org, kb: KnowledgeBase, segment: Segment) -> bool:
        """
        Delete a segment from the store.

        Args:
        - org: The organization to delete the segment from.
        - kb: The knowledge base to delete the segment from.
        - segment: The segment to be deleted.

        Returns:
        - True if the segment was successfully deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_segment(
        self, org: Org, kb: KnowledgeBase, doc_id: str, position_doc: str
    ) -> Segment:
        """
        Get a segment from the store.

        Args:
        - org: The organization to get the segment from.
        - kb: The knowledge base to get the segment from.
        - doc_id: The doc_id to search for.
        - position_doc: The position_doc to search for.

        Returns:
        - The segment with the given doc_uri and position_doc.
        """
        pass

    @abstractmethod
    def get_segment_by_uuid(
        self, org: Org, kb: KnowledgeBase, segment_uuid: str
    ) -> Segment:
        """
        Get a segment from the store by its uuid.

        Args:
        - org: The organization to get the segment from.
        - kb: The knowledge base to get the segment from.
        - segment_uuid: The uuid to search for.

        Returns:
        - The segment with the given uuid.
        """
        pass

    @abstractmethod
    def get_all_segments_for_document(
        self, org: Org, kb: KnowledgeBase, doc_id: str
    ) -> List[Segment]:
        """
        Get all segments from the store for this document.

        Args:
        - org: The organization to get the segments from.
        - kb: The knowledge base to get the segments from.
        - doc_id: The doc_id to search for.

        Returns:
        - A list of segments with the given doc_uri.
        """
        pass

    @abstractmethod
    def get_segments_for_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[Segment]:
        """
        Get all segments from the store for a docsource.

        Args:
        - org: The organization to get the segments from.
        - kb: The knowledge base to get the segments from.
        - docsource: The docsource to search for.

        Returns:
        - A list of segments with the given docsource.
        """
        pass

    @abstractmethod
    def get_parent_segment(
        self, org: Org, kb: KnowledgeBase, segment: Segment
    ) -> Optional[Segment]:
        """
        Get the parent segment for a segment.

        Args:
        - org: The organization to get the segments from.
        - kb: The knowledge base to get the segments from.
        - segment_uuid: The uuid of the segment to search for.

        Returns:
        - A list of parent segments for the given segment.
        """
        pass

    @abstractmethod
    def get_older_sibling_segment(
        self, org: Org, kb: KnowledgeBase, segment: Segment
    ) -> Optional[Segment]:
        """
        Get the sibling segments for a segment.

        Args:
        - org: The organization to get the segments from.
        - kb: The knowledge base to get the segments from.
        - segment: The segment to search for.

        Returns:
        - The older sibling segment for the given segment.
        """
        pass

    @abstractmethod
    def get_younger_sibling_segment(
        self, org: Org, kb: KnowledgeBase, segment: Segment
    ) -> Optional[Segment]:
        """
        Get the sibling segments for a segment.

        Args:
        - org: The organization to get the segments from.
        - kb: The knowledge base to get the segments from.
        - segment: The segment to search for.

        Returns:
        - The younger sibling segment for the given segment.
        """
        pass

    @abstractmethod
    def update_segment(
        self, org: Org, kb: KnowledgeBase, segment_update: SegmentUpdate
    ) -> SegmentInDB:
        """
        Update a segment in the store.

        Args:
        - org: The organization to update the segment in.
        - kb: The knowledge base to update the segment in.
        - segment_update: The segment to be updated.

        Returns:
        - The updated segment.
        """
        pass


def create_segment_store(settings: SystemSettings) -> AbstractSegmentStore:
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="segment_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractSegmentStore,
        settings=settings,
    )
