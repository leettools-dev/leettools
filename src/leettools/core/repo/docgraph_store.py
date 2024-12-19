from abc import ABC, abstractmethod

from leettools.core.schemas.segment import SegmentInDB
from leettools.settings import SystemSettings


class AbstractDocGraphStore(ABC):
    @abstractmethod
    def create_segment_node(self, segment_in_store: SegmentInDB) -> int:
        """
        Create a segment in the graph database.

        Args:
        segment_in_store: The dictionary representation of the segment.

        Returns:
        The id of the created node.
        """
        pass

    @abstractmethod
    def create_segments_relationship(
        self, parent_node_id: int, child_node_id: int
    ) -> int:
        """
        Create a BELONGS_TO relationship in the graph database.

        Args:
        parent_node_id: The id of the parent node.
        child_node_id: The id of the child node.

        Returns:
        The id of the created relationship.
        """
        pass

    @abstractmethod
    def delete_segment_node(self, segment_in_store: SegmentInDB) -> bool:
        """
        Delete a segment node from the graph database.

        Args:
        segment_in_store: The segment to be deleted.

        Returns:
        True if the segment was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def delete_segments_relationship(
        self, parent_node_id: int, child_node_id: int
    ) -> bool:
        """
        Delete a BELONGS_TO relationship from the graph database.

        Args:
        parent_node_id: The id of the parent node.
        child_node_id: The id of the child node.

        Returns:
        True if the relationship was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def update_segment_node(self, segment_in_store: SegmentInDB) -> int:
        """
        Update a segment node in the graph database.

        Args:
        segment_in_store: The segment to be updated.

        Returns:
        The id of the updated node.
        """
        pass


def create_docgraph_store(settings: SystemSettings) -> AbstractDocGraphStore:

    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="docgraph_store",
        repo_type=settings.GRAPH_STORE_TYPE,
        base_class=AbstractDocGraphStore,
        settings=settings,
    )
