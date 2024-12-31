from typing import Dict

from leettools.core.schemas.segment import Segment


class VectorDuckDBSchema:

    @classmethod
    def get_schema(cls, dense_embedder_dimension: int) -> Dict[str, str]:
        return {
            Segment.FIELD_DOCUMENT_UUID: "VARCHAR",
            Segment.FIELD_DOCSINK_UUID: "VARCHAR",
            Segment.FIELD_SEGMENT_UUID: "VARCHAR",
            Segment.FIELD_CREATED_TIMESTAMP_IN_MS: "BIGINT",
            Segment.FIELD_LABEL_TAG: "VARCHAR",
            Segment.FIELD_CONTENT: "VARCHAR",
            Segment.FIELD_EMBEDDINGS: f"FLOAT[{dense_embedder_dimension}]",
        }
