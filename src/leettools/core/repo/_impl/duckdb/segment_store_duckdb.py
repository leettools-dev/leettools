import json
import uuid
from typing import List, Optional

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.exceptions import EntityExistsException
from leettools.common.logging import logger
from leettools.context_manager import ContextManager
from leettools.core.repo._impl.duckdb.segment_store_duckdb_schema import (
    SegmentDuckDBSchema,
)
from leettools.core.repo.segment_store import AbstractSegmentStore
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

SEGMENT_COLLECTION_SUFFIX = "_segment"


class SegmentStoreDuckDB(AbstractSegmentStore):
    """DuckDB implementation of segment storage."""

    def __init__(self, settings: SystemSettings) -> None:
        """Initialize DuckDB connection."""
        self.settings = settings
        self.duckdb_client = DuckDBClient(self.settings)

    def _dict_to_segment(self, data: dict) -> Segment:
        """Convert stored dictionary to Segment."""
        # JSON decode lists/dicts
        if data.get(Segment.FIELD_EMBEDDINGS):
            try:
                data[Segment.FIELD_EMBEDDINGS] = json.loads(
                    data[Segment.FIELD_EMBEDDINGS]
                )
            except json.JSONDecodeError:
                logger().warning("Failed to decode embeddings JSON")
                data[Segment.FIELD_EMBEDDINGS] = None
        return Segment.from_segment_in_db(SegmentInDB.model_validate(data))

    def _get_table_name(self, org: Org, kb: KnowledgeBase) -> str:
        """Get the dynamic table name for the org and kb combination."""
        org_db_name = Org.get_org_db_name(org.org_id)
        collection_name = f"kb_{kb.kb_id}{SEGMENT_COLLECTION_SUFFIX}"
        return self.duckdb_client.create_table_if_not_exists(
            org_db_name,
            collection_name,
            SegmentDuckDBSchema.get_schema(),
        )

    def _segment_to_dict(self, segment: SegmentInDB) -> dict:
        """Convert SegmentInDB to dictionary for storage."""
        data = segment.model_dump()
        # JSON encode lists/dicts
        if data.get(Segment.FIELD_EMBEDDINGS):
            data[Segment.FIELD_EMBEDDINGS] = json.dumps(data[Segment.FIELD_EMBEDDINGS])
        return data

    def create_segment(
        self, org: Org, kb: KnowledgeBase, segment_create: SegmentCreate
    ) -> Segment:
        """Create a new segment."""
        # Check if segment already exists
        existing_segment = self.get_segment(
            org, kb, segment_create.document_uuid, segment_create.position_in_doc
        )
        if existing_segment is not None:
            if existing_segment.content == segment_create.content:
                logger().debug(
                    f"Segment {segment_create.document_uuid} at {segment_create.position_in_doc} "
                    "already exists in the collection. Most likely it is created by a "
                    "partially finished operation."
                )
                return existing_segment
            else:
                raise EntityExistsException(
                    entity_name=f"{segment_create.document_uuid} at {segment_create.position_in_doc}",
                    entity_type="Segment",
                )

        table_name = self._get_table_name(org, kb)
        segment_in_db = SegmentInDB.from_segment_create(segment_create)
        data = self._segment_to_dict(segment_in_db)
        data[Segment.FIELD_SEGMENT_UUID] = str(uuid.uuid4())

        column_list = list(data.keys())
        value_list = list(data.values())

        # Execute insert
        self.duckdb_client.insert_into_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
        )

        return self._dict_to_segment(data)

    def delete_segment(self, org: Org, kb: KnowledgeBase, segment: Segment) -> bool:
        """Delete a segment by UUID."""
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} = ?"
        value_list = [segment.segment_uuid]
        self.duckdb_client.delete_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def delete_segment_by_pos(
        self, org: Org, kb: KnowledgeBase, doc_id: str, position_in_doc: str
    ) -> bool:
        """Delete a segment by document ID and position."""
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ? AND {Segment.FIELD_POSITION_IN_DOC} = ?"
        value_list = [doc_id, position_in_doc]
        self.duckdb_client.delete_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def get_all_segments_for_document(
        self, org: Org, kb: KnowledgeBase, doc_id: str
    ) -> List[Segment]:
        """Get all segments for a document, ordered by position."""
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ? ORDER BY {Segment.FIELD_POSITION_IN_DOC}"
        value_list = [doc_id]
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_segment(row) for row in results]

    def get_older_sibling_segment(
        self, org: Org, kb: KnowledgeBase, segment: Segment
    ) -> Optional[Segment]:
        """Get the previous sibling segment."""
        table_name = self._get_table_name(org, kb)
        where_clause = (
            f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ? AND {Segment.FIELD_POSITION_IN_DOC} < ?"
            f" AND length({Segment.FIELD_POSITION_IN_DOC}) = length(?)"
            f"ORDER BY {Segment.FIELD_POSITION_IN_DOC} DESC LIMIT 1"
        )
        value_list = [
            segment.document_uuid,
            segment.position_in_doc,
            segment.position_in_doc,
        ]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return self._dict_to_segment(result) if result else None

    def get_parent_segment(
        self, org: Org, kb: KnowledgeBase, segment: Segment
    ) -> Optional[Segment]:
        """Get parent segment based on position hierarchy."""
        table_name = self._get_table_name(org, kb)
        where_clause = (
            f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ? AND {Segment.FIELD_POSITION_IN_DOC} < ?"
            f" AND length({Segment.FIELD_POSITION_IN_DOC}) < length(?)"
            f"ORDER BY {Segment.FIELD_POSITION_IN_DOC} DESC LIMIT 1"
        )
        value_list = [
            segment.document_uuid,
            segment.position_in_doc,
            segment.position_in_doc,
        ]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return self._dict_to_segment(result) if result else None

    def get_segment(
        self, org: Org, kb: KnowledgeBase, doc_id: str, position_in_doc: str
    ) -> Optional[Segment]:
        """
        Get a segment by document ID and position.
        Returns None if no segment exists with the given combination.
        """
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ? AND {Segment.FIELD_POSITION_IN_DOC} = ?"
        value_list = [doc_id, position_in_doc]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return self._dict_to_segment(result) if result else None

    def get_segment_by_uuid(
        self, org: Org, kb: KnowledgeBase, segment_uuid: str
    ) -> Optional[Segment]:
        """Get a segment by UUID."""
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} = ?"
        value_list = [segment_uuid]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return self._dict_to_segment(result) if result else None

    def get_segments_for_document(
        self, org: Org, kb: KnowledgeBase, document_uuid: str
    ) -> List[Segment]:
        """Get all segments for a document."""
        table_name = self._get_table_name(org, kb)
        where_clause = f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ? ORDER BY {Segment.FIELD_POSITION_IN_DOC}"
        value_list = [document_uuid]
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [self._dict_to_segment(row) for row in results]

    def get_segments_for_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[Segment]:
        """
        Get all segments for a docsource.

        Since we no longer have a direct relationship between docsource and segment,
        we need to first get all documents for the docsource and then get all segments
        for each document.

        This function should not used in regular queries, as it is inefficient.
        """
        table_name = self._get_table_name(org, kb)

        context = ContextManager().get_context()
        repo_manager = context.get_repo_manager()
        doc_store = repo_manager.get_document_store()
        all_segments: List[Segment] = []
        for doc in doc_store.get_documents_for_docsource(org, kb, docsource):
            document_uuid = doc.document_uuid
            where_clause = f"WHERE {Segment.FIELD_DOCUMENT_UUID} = '{document_uuid}'"

            results = self.duckdb_client.fetch_all_from_table(
                table_name=table_name,
                where_clause=where_clause,
            )
            segments = [self._dict_to_segment(row) for row in results]
            if results:
                all_segments.extend(segments)

        return all_segments

    def get_younger_sibling_segment(
        self, org: Org, kb: KnowledgeBase, segment: Segment
    ) -> Optional[Segment]:
        """Get the next sibling segment."""
        table_name = self._get_table_name(org, kb)
        where_clause = (
            f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ? AND {Segment.FIELD_POSITION_IN_DOC} > ?"
            f" AND length({Segment.FIELD_POSITION_IN_DOC}) = length(?)"
            f"ORDER BY {Segment.FIELD_POSITION_IN_DOC} LIMIT 1"
        )
        value_list = [
            segment.document_uuid,
            segment.position_in_doc,
            segment.position_in_doc,
        ]
        result = self.duckdb_client.fetch_one_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return self._dict_to_segment(result) if result else None

    def update_segment(
        self, org: Org, kb: KnowledgeBase, segment_update: SegmentUpdate
    ) -> Optional[Segment]:
        """Update an existing segment."""
        table_name = self._get_table_name(org, kb)
        segment_in_db = SegmentInDB.from_segment_update(segment_update)
        data = self._segment_to_dict(segment_in_db)
        segment_uuid = data.pop(Segment.FIELD_SEGMENT_UUID)

        column_list = list(data.keys())
        value_list = list(data.values())
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} = ?"
        value_list = value_list + [segment_uuid]
        self.duckdb_client.update_table(
            table_name=table_name,
            column_list=column_list,
            value_list=value_list,
            where_clause=where_clause,
        )
        data[Segment.FIELD_SEGMENT_UUID] = segment_uuid
        return self._dict_to_segment(data)
