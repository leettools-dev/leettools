from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.common.utils import time_utils
from leettools.common.utils.obj_utils import add_fieldname_constants, assign_properties

"""
See [README](./README.md) about the usage of different pydantic models.
"""


class SegmentStatus(str, Enum):
    CREATED = "Created"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class SegmentBase(BaseModel):
    content: str = Field(..., description="The content of the segment")
    document_uuid: str = Field(
        ..., description="The UUID of the document the segment belongs to"
    )
    doc_uri: str = Field(..., description="The URI of the document")
    docsink_uuid: str = Field(
        ..., description="The UUID of the document sink the document belongs to"
    )
    kb_id: str = Field(
        ..., description="The ID of the knowledge base the document belongs to"
    )
    position_in_doc: str = Field(
        ..., description="The position of the segment in the document, such as '2.3.2'"
    )

    original_uri: Optional[str] = Field(
        None, description="The original URI of the document the segment belongs to"
    )
    heading: Optional[str] = Field(None, description="The heading of the segment")
    start_offset: Optional[int] = Field(
        None, description="The start offset of the segment in the document"
    )
    end_offset: Optional[int] = Field(
        None, description="The end offset of the segment in the document"
    )

    # the date tags of the segment, could be used for search
    # User can specify the date tag, if not specified, it will be the current time
    created_timestamp_in_ms: Optional[int] = Field(
        None, description="The timestamp in milliseconds when the segment was created"
    )

    # the label tag of the segment, could be used for search
    # right now only one label tag is supported
    label_tag: Optional[str] = Field(None, description="The label tag of the segment")


class SegmentCreate(SegmentBase):
    pass


class SegmentInDBBase(SegmentBase):
    # The UUID of the segment after it has been stored
    segment_uuid: str = Field(..., description="The UUID of the segment")

    segment_status: Optional[SegmentStatus] = Field(
        None, description="The status of the segment"
    )

    # the embeddings of the segment
    embeddings: Optional[List[float]] = Field(
        [], description="The embeddings of the segment"
    )

    # The date the segment was created
    created_at: Optional[datetime] = Field(
        None, description="The date the segment was created in the database"
    )

    # The date the document was updated
    updated_at: Optional[datetime] = Field(
        None, description="The date the segment was updated in the database"
    )

    # The id of the graph node that represents the segment
    graph_node_id: Optional[int] = Field(
        None,
        description=(
            "The id of the graph node that represents the segment if we have a document graph"
        ),
    )


class SegmentUpdate(SegmentInDBBase):
    pass


class SegmentInDB(SegmentInDBBase):
    @classmethod
    def from_segment_create(
        SegmentInDB, segment_create: SegmentCreate
    ) -> "SegmentInDB":
        ct = time_utils.current_datetime()
        if segment_create.created_timestamp_in_ms is None:
            segment_create.created_timestamp_in_ms = int(ct.timestamp() * 1000)
        segment_in_db = SegmentInDB(
            # caller needs to update uuid later document is
            # stored in store and get the uuid back.
            segment_uuid="",
            content=segment_create.content,
            document_uuid=segment_create.document_uuid,
            doc_uri=segment_create.doc_uri,
            docsink_uuid=segment_create.docsink_uuid,
            kb_id=segment_create.kb_id,
            position_in_doc=segment_create.position_in_doc,
            original_uri=segment_create.original_uri,
            heading=segment_create.heading,
            start_offset=segment_create.start_offset,
            end_offset=segment_create.end_offset,
            created_at=ct,
            updated_at=ct,
            created_timestamp_in_ms=segment_create.created_timestamp_in_ms,
            label_tag=segment_create.label_tag,
        )
        assign_properties(segment_in_db, segment_create)
        return segment_in_db

    @classmethod
    def from_segment_update(
        SegmentInDB, segment_update: SegmentUpdate
    ) -> "SegmentInDB":
        segment_in_db = SegmentInDB(
            segment_uuid=segment_update.segment_uuid,
            content=segment_update.content,
            document_uuid=segment_update.document_uuid,
            doc_uri=segment_update.doc_uri,
            docsink_uuid=segment_update.docsink_uuid,
            kb_id=segment_update.kb_id,
            position_in_doc=segment_update.position_in_doc,
            original_uri=segment_update.original_uri,
            heading=segment_update.heading,
            start_offset=segment_update.start_offset,
            end_offset=segment_update.end_offset,
            embeddings=segment_update.embeddings,
            updated_at=time_utils.current_datetime(),
        )
        assign_properties(segment_in_db, segment_update)
        return segment_in_db


@add_fieldname_constants
class Segment(SegmentInDBBase):
    """
    The result after we chunk the document into segments.
    """

    @classmethod
    def from_segment_in_db(Segment, segment_in_db: SegmentInDB) -> "Segment":
        segment = Segment(
            segment_uuid=segment_in_db.segment_uuid,
            content=segment_in_db.content,
            document_uuid=segment_in_db.document_uuid,
            doc_uri=segment_in_db.doc_uri,
            docsink_uuid=segment_in_db.docsink_uuid,
            kb_id=segment_in_db.kb_id,
            position_in_doc=segment_in_db.position_in_doc,
            original_uri=segment_in_db.original_uri,
            start_offset=segment_in_db.start_offset,
            end_offset=segment_in_db.end_offset,
            embeddings=segment_in_db.embeddings,
            created_at=segment_in_db.created_at,
            updated_at=segment_in_db.updated_at,
            created_timestamp_in_ms=segment_in_db.created_timestamp_in_ms,
            label_tag=segment_in_db.label_tag,
        )
        assign_properties(segment, segment_in_db)
        return segment


class SearchResultSegment(Segment):
    # The search score of the segment returned by the search engine
    search_score: Optional[float] = None
    vector_type: Optional[str] = None
    content_display: Optional[str] = None

    @classmethod
    def from_segment(
        SearchResultSegment,
        segment: Segment,
        search_score: float,
        vector_type: str = None,
    ) -> "SearchResultSegment":
        search_result_segment = SearchResultSegment(
            segment_uuid=segment.segment_uuid,
            content=segment.content,
            document_uuid=segment.document_uuid,
            doc_uri=segment.doc_uri,
            docsink_uuid=segment.docsink_uuid,
            kb_id=segment.kb_id,
            position_in_doc=segment.position_in_doc,
            original_uri=segment.original_uri,
            start_offset=segment.start_offset,
            end_offset=segment.end_offset,
            embeddings=segment.embeddings,
            created_at=segment.created_at,
            updated_at=segment.updated_at,
            search_score=search_score,
            vector_type=vector_type,
        )
        assign_properties(search_result_segment, segment)
        return search_result_segment


@dataclass
class BaseSegmentSchema(ABC):
    """Abstract base schema for segment implementations."""

    TABLE_NAME: str = "TABLE_NAME"

    @classmethod
    @abstractmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get database-specific schema definition."""

    @classmethod
    def get_base_columns(cls) -> Dict[str, str]:
        """Get base column definitions shared across implementations."""
        return {
            Segment.FIELD_SEGMENT_UUID: "VARCHAR PRIMARY KEY",
            Segment.FIELD_DOCUMENT_UUID: "VARCHAR NOT NULL",
            Segment.FIELD_DOC_URI: "VARCHAR NOT NULL",
            Segment.FIELD_DOCSINK_UUID: "VARCHAR NOT NULL",
            Segment.FIELD_KB_ID: "VARCHAR NOT NULL",
            Segment.FIELD_CONTENT: "TEXT NOT NULL",
            Segment.FIELD_POSITION_IN_DOC: "VARCHAR NOT NULL",
            Segment.FIELD_ORIGINAL_URI: "VARCHAR",
            Segment.FIELD_HEADING: "VARCHAR",
            Segment.FIELD_START_OFFSET: "INTEGER",
            Segment.FIELD_END_OFFSET: "INTEGER",
            Segment.FIELD_CREATED_TIMESTAMP_IN_MS: "BIGINT",
            Segment.FIELD_LABEL_TAG: "VARCHAR",
            Segment.FIELD_EMBEDDINGS: "JSON",
            Segment.FIELD_SEGMENT_STATUS: "VARCHAR",
            Segment.FIELD_GRAPH_NODE_ID: "INTEGER",
            Segment.FIELD_CREATED_AT: "TIMESTAMP",
            Segment.FIELD_UPDATED_AT: "TIMESTAMP",
        }
