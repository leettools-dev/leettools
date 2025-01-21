from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Dict, List

import numpy as np

from leettools.common.duckdb.duckdb_client import DuckDBClient
from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.repo._impl.duckdb.vector_store_duckdb_schema import (
    VectorDuckDBSchema,
)
from leettools.core.repo.vector_store import (
    AbstractVectorStore,
    VectorSearchResult,
    VectorType,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.eds.rag.search.filter import Filter
from leettools.eds.rag.search.filter_duckdb import to_duckdb_filter
from leettools.eds.str_embedder.dense_embedder import (
    AbstractDenseEmbedder,
    create_dense_embedder_for_kb,
)
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)

DENSE_VECTOR_COLLECTION_SUFFIX = "_dense_vectors"
SIMILARITY_METRIC_ATTR = "similarity_metric"


class VectorStoreDuckDBDense(AbstractVectorStore):
    def __init__(self, context: Context) -> None:
        """Initialize DuckDB connection."""
        logger().debug("Initializing VectorStoreDuckDBDense")
        self.context = context
        self.settings = context.settings
        self.duckdb_client = DuckDBClient(self.settings)

    def _batch_get_embedding(
        self, dense_embedder: AbstractDenseEmbedder, segment_batch: List[Segment]
    ) -> List[Segment]:
        """
        Return the chunk_batch as well as the embeddings for each chunk so that
        we can aggregate them and save them to the database together.

        Args:
        - dense_embedder: Dense embedder to use
        - segment_batch: List of segments to get embeddings for

        Returns:
        - List of segments with embeddings
        """
        texts = [segment.content for segment in segment_batch]
        embeddings = self._get_embedding(dense_embedder, texts)
        for i in range(len(segment_batch)):
            normalized_vector = self._normalize_vector(embeddings[i])
            segment_batch[i].embeddings = normalized_vector
        return segment_batch

    def _batch_upsert_embeddings(
        self, table_name: str, segments: List[Segment]
    ) -> None:
        # get a list of segment_uuids
        segment_uuids = [segment.segment_uuid for segment in segments]
        # delete the existing embeddings for the segment_uuids
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} IN ({','.join(['?'] * len(segment_uuids))})"
        value_list = segment_uuids
        self.duckdb_client.delete_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )

        # insert the new embeddings for the segment_uuids
        column_list = [
            Segment.FIELD_EMBEDDINGS,
            Segment.FIELD_CONTENT,
            Segment.FIELD_CREATED_TIMESTAMP_IN_MS,
            Segment.FIELD_LABEL_TAG,
            Segment.FIELD_DOCUMENT_UUID,
            Segment.FIELD_DOCSINK_UUID,
            Segment.FIELD_SEGMENT_UUID,
        ]

        # the value list should be a list of tuples, like (), ()
        value_list = []
        for segment in segments:
            if segment.created_timestamp_in_ms is None:
                segment.created_timestamp_in_ms = 0
            if segment.label_tag is None:
                segment.label_tag = ""
            item_list = [
                segment.embeddings,
                segment.content,
                segment.created_timestamp_in_ms,
                segment.label_tag,
                segment.document_uuid,
                segment.docsink_uuid,
                segment.segment_uuid,
            ]
            value_list.append(item_list)
        self.duckdb_client.batch_insert_into_table(
            table_name=table_name,
            column_list=column_list,
            values=value_list,
        )

    def _get_embedding(
        self, dense_embedder: AbstractDenseEmbedder, texts: List[str]
    ) -> List[List[float]]:
        if len(texts) == 0:
            return []

        embed_request = DenseEmbeddingRequest(sentences=texts)
        embed_result: DenseEmbeddings = dense_embedder.embed(embed_request)
        return embed_result.dense_embeddings

    def _get_table_name(
        self, org: Org, kb: KnowledgeBase, dense_embedder_dimension: int = None
    ) -> str:
        """Get the dynamic table name for the org and kb combination."""
        org_db_name = Org.get_org_db_name(org.org_id)
        collection_name = f"kb_{kb.kb_id}{DENSE_VECTOR_COLLECTION_SUFFIX}"
        if dense_embedder_dimension is not None:
            install_fts_sql = "INSTALL fts; LOAD fts;"
            return self.duckdb_client.create_table_if_not_exists(
                schema_name=org_db_name,
                table_name=collection_name,
                columns=VectorDuckDBSchema.get_schema(dense_embedder_dimension),
                create_sequence_sql=install_fts_sql,
            )
        else:
            return self.duckdb_client.get_table(org_db_name, collection_name)

    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """
        Normalize a vector.

        Args:
            vector: The vector to normalize.

        Returns:
            The normalized vector with values rounded to 7 decimal places.
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            normalized_vector = vector
        else:
            normalized_vector = vector / norm

        return normalized_vector

    def _upsert_embeddings_into_duckdb(
        self,
        org: Org,
        kb: KnowledgeBase,
        segments: List[Segment],
        dense_embedder: AbstractDenseEmbedder,
    ) -> bool:
        table_name = self._get_table_name(org, kb, dense_embedder.get_dimension())
        embed_batch_size = 50
        query_batch_size = 100

        # divide the segments into batches based on the embed_batch_size
        embed_batches = []
        for i in range(0, len(segments), embed_batch_size):
            batch = segments[i : i + embed_batch_size]
            embed_batches.append(batch)

        # get the embeddings for the segments
        partial_get_embedding = partial(self._batch_get_embedding, dense_embedder)
        with ThreadPoolExecutor(max_workers=10) as executor:
            rtn_list = list(executor.map(partial_get_embedding, embed_batches))

        segments_with_embeddings = [item for sublist in rtn_list for item in sublist]

        # divide the segments into batches based on the query_batch_size
        insert_batches = []
        for i in range(0, len(segments_with_embeddings), query_batch_size):
            batch = segments_with_embeddings[i : i + query_batch_size]
            insert_batches.append(batch)

        partial_batch_upsert_embeddings = partial(
            self._batch_upsert_embeddings, table_name
        )
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(partial_batch_upsert_embeddings, insert_batches)
        return True

    def save_segments(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        segments: List[Segment],
    ) -> bool:
        """Save a list of segments into the store."""
        dense_embedder = create_dense_embedder_for_kb(org, kb, user, self.context)
        return self._upsert_embeddings_into_duckdb(org, kb, segments, dense_embedder)

    def delete_segment_vector(
        self, org: Org, kb: KnowledgeBase, segment_uuid: str
    ) -> bool:
        """Delete a segment vector from the store."""
        table_name = self._get_table_name(org, kb)
        if table_name is None:
            return False
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} = ?"
        value_list = [segment_uuid]
        self.duckdb_client.delete_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def delete_segment_vectors_by_docsink_uuid(
        self, org: Org, kb: KnowledgeBase, docsink_uuid: str
    ) -> bool:
        """Delete a list of segment vectors from the store by docsink uuid."""
        table_name = self._get_table_name(org, kb)
        if table_name is None:
            return False

        where_clause = f"WHERE {Segment.FIELD_DOCSINK_UUID} = ?"
        value_list = [docsink_uuid]
        self.duckdb_client.delete_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def delete_segment_vectors_by_docsource_uuid(
        self, org: Org, kb: KnowledgeBase, docsource_uuid: str
    ) -> bool:
        """Delete a list of segment vectors from the store by docsource uuid."""
        table_name = self._get_table_name(org, kb)
        if table_name is None:
            return False

        repo_manger = self.context.get_repo_manager()
        docsource = repo_manger.get_docsource_store().get_docsource(
            org, kb, docsource_uuid
        )
        documents = repo_manger.get_document_store().get_documents_for_docsource(
            org, kb, docsource
        )
        deleted = False
        for document in documents:
            if self.delete_segment_vectors_by_document_id(
                org, kb, document.document_uuid
            ):
                deleted = True
        return deleted

    def delete_segment_vectors_by_document_id(
        self, org: Org, kb: KnowledgeBase, document_uuid: str
    ) -> bool:
        """Delete a list of segment vectors from the store by document id."""
        table_name = self._get_table_name(org, kb)
        if table_name is None:
            return False
        where_clause = f"WHERE {Segment.FIELD_DOCUMENT_UUID} = ?"
        value_list = [document_uuid]
        self.duckdb_client.delete_from_table(
            table_name=table_name,
            where_clause=where_clause,
            value_list=value_list,
        )
        return True

    def get_segment_vector(
        self, org: Org, kb: KnowledgeBase, segment_uuid: str
    ) -> List[float]:
        """Get a segment vector from the store."""
        table_name = self._get_table_name(org, kb)
        if table_name is None:
            return []

        column_list = [Segment.FIELD_EMBEDDINGS]
        where_clause = f"WHERE {Segment.FIELD_SEGMENT_UUID} = ?"
        value_list = [segment_uuid]
        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            column_list=column_list,
            where_clause=where_clause,
            value_list=value_list,
        )
        if len(results) == 1:
            return results[0][Segment.FIELD_EMBEDDINGS]
        else:
            if len(results) > 1:
                logger().error(
                    f"Segment vector with uuid '{segment_uuid}' is not unique!"
                )
                return None
            else:
                return []

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
        """Search for segments in the store."""
        # Implement your search logic here
        dense_embedder = create_dense_embedder_for_kb(org, kb, user, self.context)
        embedding_dimension = dense_embedder.get_dimension()
        table_name = self._get_table_name(org, kb, embedding_dimension)
        embed_request = DenseEmbeddingRequest(sentences=[query])
        embed_result: DenseEmbeddings = dense_embedder.embed(embed_request)
        query_vector: List[float] = embed_result.dense_embeddings[0]
        query_vector: List[float] = self._normalize_vector(query_vector)

        column_list = [
            Segment.FIELD_SEGMENT_UUID,
            f"array_cosine_similarity({Segment.FIELD_EMBEDDINGS}, "
            f"CAST(? AS FLOAT[{embedding_dimension}])) AS {SIMILARITY_METRIC_ATTR}",
        ]

        order_clause = f"ORDER BY {SIMILARITY_METRIC_ATTR} DESC LIMIT ?"
        value_list = [query_vector]

        if filter is not None:
            # duckdb does not support double quotes in the where clause
            filter_expr, fields, values = to_duckdb_filter(filter)
            where_clause = f"WHERE {filter_expr} {order_clause}"

            for column in fields:
                if column not in column_list:
                    column_list.append(column)
            value_list.extend(values)
        else:
            where_clause = order_clause

        value_list.append(top_k)

        results = self.duckdb_client.fetch_all_from_table(
            table_name=table_name,
            column_list=column_list,
            where_clause=where_clause,
            value_list=value_list,
        )
        return [
            VectorSearchResult(
                segment_uuid=result[Segment.FIELD_SEGMENT_UUID],
                search_score=result[SIMILARITY_METRIC_ATTR],
                vector_type=VectorType.DENSE,
            )
            for result in results
        ]

    def update_segment_vector(
        self, org: Org, kb: KnowledgeBase, user: User, segment: Segment
    ) -> bool:
        """Update a segment vector in the store."""
        dense_embedder = create_dense_embedder_for_kb(org, kb, user, self.context)
        return self._upsert_embeddings_into_duckdb(org, kb, [segment], dense_embedder)

    def full_text_search_in_kb(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        query: str,
        top_k: int,
        search_params: Dict[str, Any] = None,
        filter_expr: str = None,
    ) -> List[VectorSearchResult]:
        """Search for segments in the store."""
        # Implement your search logic here
        dense_embedder = create_dense_embedder_for_kb(org, kb, user, self.context)
        embedding_dimension = dense_embedder.get_dimension()
        table_name = self._get_table_name(org, kb, embedding_dimension)

        where_clause = ""
        if filter_expr is not None:
            # duckdb does not support double quotes in the where clause
            filter_expr = filter_expr.replace('"', "'")
            where_clause = f"WHERE {filter_expr} and score is not null"
        else:
            where_clause = "WHERE score is not null"

        query_statement = f"""
            SELECT *, fts_{table_name.replace('.', '_')}.match_bm25(
                {Segment.FIELD_SEGMENT_UUID},
                ?,
                fields := '{Segment.FIELD_CONTENT}'
            ) AS score
            FROM {table_name}
            {where_clause}
            ORDER BY score DESC LIMIT ?;
        """
        value_list = [query, top_k]
        results = self.duckdb_client.execute_and_fetch_all(query_statement, value_list)
        return [
            VectorSearchResult(
                segment_uuid=result[Segment.FIELD_SEGMENT_UUID],
                search_score=result["score"],
                vector_type=VectorType.SPARSE,
            )
            for result in results
        ]

    def rebuild_full_text_index(self, org: Org, kb: KnowledgeBase, user: User) -> None:
        dense_embedder = create_dense_embedder_for_kb(org, kb, user, self.context)
        embedding_dimension = dense_embedder.get_dimension()
        table_name = self._get_table_name(org, kb, embedding_dimension)
        rebuild_fts_index_sql = f"""
        PRAGMA create_fts_index({table_name}, {Segment.FIELD_SEGMENT_UUID}, {Segment.FIELD_CONTENT}, stemmer = 'porter',
            stopwords = 'english', ignore = '(\\.|[^a-z])+',
            strip_accents = 1, lower = 1, overwrite = 0)        
        """
        self.duckdb_client.execute_sql(rebuild_fts_index_sql)
