from typing import Dict

from leettools.core.schemas.segment import Segment

GRAPH_DB_NAME = "docgraph"
GRAPH_NODE_ID_ATTR = "graph_node_id"


class DocGraphNodeDuckDBSchema:
    TABLE_NAME = "node"

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        return {
            Segment.FIELD_DOCUMENT_UUID: "VARCHAR",
            GRAPH_NODE_ID_ATTR: "INTEGER DEFAULT nextval('graph_node_id_seq')",
            Segment.FIELD_SEGMENT_UUID: "VARCHAR",
            Segment.FIELD_START_OFFSET: "INTEGER",
            Segment.FIELD_END_OFFSET: "INTEGER",
            Segment.FIELD_HEADING: "VARCHAR",
        }

    @classmethod
    def get_create_sequence_sql(cls) -> str:
        return "CREATE SEQUENCE IF NOT EXISTS graph_node_id_seq START 1"


RELATIONSHIP_ID_ATTR = "relationship_id"
PARENT_NODE_ID_ATTR = "parent_node_id"
CHILD_NODE_ID_ATTR = "child_node_id"


class DocGraphRelationshipDuckDBSchema:
    TABLE_NAME = "relationship"

    @classmethod
    def get_schema(cls) -> Dict[str, str]:
        return {
            RELATIONSHIP_ID_ATTR: "INTEGER DEFAULT nextval('relationship_id_seq')",
            PARENT_NODE_ID_ATTR: "INTEGER",
            CHILD_NODE_ID_ATTR: "INTEGER",
        }

    @classmethod
    def get_create_sequence_sql(cls) -> str:
        return "CREATE SEQUENCE IF NOT EXISTS relationship_id_seq START 1"
