from typing import Any, Dict, List

from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.repo.vector_store import (
    VectorSearchResult,
    create_vector_store_dense,
)
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SearchResultSegment
from leettools.core.schemas.user import User
from leettools.eds.rag.search.filter import Filter
from leettools.eds.rag.search.searcher import AbstractSearcher


class SearcherSimple(AbstractSearcher):
    def __init__(self, context: Context) -> None:
        repo_manager = context.get_repo_manager()
        self.dense_vectorstore = create_vector_store_dense(context)
        self.segmentstore = repo_manager.get_segment_store()

    def execute_kb_search(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        query: str,
        rewritten_query: str,
        top_k: int,
        search_params: Dict[str, Any],
        query_meta: ChatQueryMetadata,
        filter: Filter = None,
    ) -> List[SearchResultSegment]:
        """
        Using vector search to get related segments in the vector DB.

        Args:
        - org: The organization.
        - kb: The knowledge base.
        - user: The user.
        - query: The original query.
        - rewritten_query: The rewritten query.
        - top_k: The number of top results to retrieve.
        - search_params: Additional search parameters.
        - query_meta: The query metadata.
        - filter: The filter for the query Defaults to None.

        Returns:
        - List[SearchResultSegment]: The list of search result segments.
        """
        logger().debug(f"The filter is: {filter} for query {query}")
        results: List[VectorSearchResult] = self.dense_vectorstore.search_in_kb(
            org=org,
            kb=kb,
            user=user,
            query=rewritten_query,
            top_k=top_k,
            search_params=search_params,
            filter=filter,
        )
        logger().debug(
            f"Found segments through dense vector search in KB: {len(results)}"
        )
        rtn_list = []
        for result in results:
            segment = self.segmentstore.get_segment_by_uuid(
                org, kb, result.segment_uuid
            )
            if segment is None:
                logger().warning(
                    f"Simple search returned segment {result.segment_uuid} not found in "
                    "segment store, maybe from a deleted document."
                )
                self.dense_vectorstore.delete_segment_vector(
                    org, kb, result.segment_uuid
                )
                continue
            rtn_list.append(
                SearchResultSegment.from_segment(segment, result.search_score)
            )
        return rtn_list
