import uuid

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.core.repo._impl.duckdb.docgraph_store_duckdb_schema import (
    CHILD_NODE_ID_ATTR,
    GRAPH_DB_NAME,
    PARENT_NODE_ID_ATTR,
    DocGraphNodeDuckDBSchema,
    DocGraphRelationshipDuckDBSchema,
)
from leettools.core.repo.docgraph_store import AbstractDocGraphStore
from leettools.core.schemas.segment import Segment, SegmentInDB
from leettools.settings import SystemSettings


class GraphStoreDuckDB(AbstractDocGraphStore):
    """The AbstractGraphStore implementation for DuckDB."""

    def __init__(self, settings: SystemSettings):
        """
        Initialize the DuckDB graph store.
        """
        super().__init__()
        self.duckdb_client = DuckDBClient(settings)
        self.node_table_name = self._get_node_table_name()
        self.relationship_table_name = self._get_relationship_table_name()

    def _get_node_table_name(self) -> str:
        db_name = GRAPH_DB_NAME
        return self.duckdb_client.create_table_if_not_exists(
            db_name,
            DocGraphNodeDuckDBSchema.TABLE_NAME,
            DocGraphNodeDuckDBSchema.get_schema(),
            DocGraphNodeDuckDBSchema.get_create_sequence_sql(),
        )

    def _get_relationship_table_name(self) -> str:
        db_name = GRAPH_DB_NAME
        return self.duckdb_client.create_table_if_not_exists(
            db_name,
            DocGraphRelationshipDuckDBSchema.TABLE_NAME,
            DocGraphRelationshipDuckDBSchema.get_schema(),
            DocGraphRelationshipDuckDBSchema.get_create_sequence_sql(),
        )

    def create_segment_node(self, segment_in_db: SegmentInDB) -> int:
        """
        Create a segment in the graph database.

        Args:
        segment_in_db: The segment to be created.

        Returns:
        The id of the node.
        """
        segment_uuid = segment_in_db.segment_uuid
        doc_id = segment_in_db.document_uuid
        heading = segment_in_db.heading
        start = segment_in_db.start_offset
        offset = segment_in_db.end_offset
        if heading == "Root":
            segment_uuid = str(uuid.uuid4())

        column_list = [
            Segment.FIELD_SEGMENT_UUID,
            Segment.FIELD_DOCUMENT_UUID,
            Segment.FIELD_HEADING,
            Segment.FIELD_START_OFFSET,
            Segment.FIELD_END_OFFSET,
        ]
        value_list = [segment_uuid, doc_id, heading, start, offset]
        self.duckdb_client.insert_into_table(
            table_name=self.node_table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return self.duckdb_client.fetch_sequence_current_value("graph_node_id_seq")

    def create_segments_relationship(self, parent_id: int, child_id: int) -> int:
        """
        Create a BELONGS_TO relationship in the graph database.

        Args:
        parent_id: The id of the parent node.
        child_id: The id of the child node.

        Returns:
        The id of the created relationship.
        """
        column_list = [PARENT_NODE_ID_ATTR, CHILD_NODE_ID_ATTR]
        value_list = [parent_id, child_id]
        self.duckdb_client.insert_into_table(
            table_name=self.relationship_table_name,
            column_list=column_list,
            value_list=value_list,
        )
        return self.duckdb_client.fetch_sequence_current_value("relationship_id_seq")

    def delete_segment_node(self, segment_in_db: SegmentInDB) -> bool:
        """
        Delete a segment node from the graph database.

        Args:
        segment_in_db: The segment to be deleted.

        Returns:
        True if the segment was deleted, False otherwise.
        """
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} = ?"
        value_list = [segment_in_db.segment_uuid]
        self.duckdb_client.delete_from_table(
            table_name=self.node_table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def delete_segments_relationship(self, parent_id: int, child_id: int) -> bool:
        """
        Delete a BELONGS_TO relationship from the graph database.

        Args:
        parent_id: The id of the parent node.
        child_id: The id of the child node.

        Returns:
        True if the relationship was deleted, False otherwise.
        """
        where_clause = f"WHERE {PARENT_NODE_ID_ATTR} = ? AND {CHILD_NODE_ID_ATTR} = ?"
        value_list = [parent_id, child_id]
        self.duckdb_client.delete_from_table(
            table_name=self.relationship_table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def update_segment_node(self, segment_in_db: SegmentInDB) -> int:
        """
        Update a segment node in the graph database.

        Args:
        segment_in_db: The segment to be updated.

        Returns:
        The id of the updated node.
        """
        segment_uuid = segment_in_db.segment_uuid
        doc_id = segment_in_db.document_uuid
        heading = segment_in_db.heading
        start = segment_in_db.start_offset
        offset = segment_in_db.end_offset
        column_list = [
            Segment.FIELD_HEADING,
            Segment.FIELD_DOCUMENT_UUID,
            Segment.FIELD_START_OFFSET,
            Segment.FIELD_END_OFFSET,
        ]
        value_list = [heading, doc_id, start, offset, segment_uuid]
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} = ?"
        self.duckdb_client.update_table(
            table_name=self.node_table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        return segment_uuid
