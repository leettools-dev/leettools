from typing import Dict

DOC_ID_ATTR = "doc_id"
DOCSOURCE_UUID_ATTR = "docsource_uuid"
DOCSINK_UUID_ATTR = "docsink_uuid"
SEGMENT_UUID_ATTR = "segment_uuid"
TIMESTAMP_TAG_IN_MS_ATTR = "timestamp_tag_in_ms"
LABEL_TAG_ATTR = "label_tag"
CONTENT_ATTR = "content"


class VectorDuckDBSchema:

    @classmethod
    def get_schema(cls, dense_embedder_dimension: int) -> Dict[str, str]:
        return {
            DOC_ID_ATTR: "VARCHAR",
            DOCSOURCE_UUID_ATTR: "VARCHAR",
            DOCSINK_UUID_ATTR: "VARCHAR",
            SEGMENT_UUID_ATTR: "VARCHAR",
            TIMESTAMP_TAG_IN_MS_ATTR: "BIGINT",
            LABEL_TAG_ATTR: "VARCHAR",
            CONTENT_ATTR: f"FLOAT[{dense_embedder_dimension}]",
        }
