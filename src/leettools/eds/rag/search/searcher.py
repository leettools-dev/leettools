import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import click

from leettools.common.exceptions import UnexpectedCaseException
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.segment_embedder_type import SegmentEmbedderType
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SearchResultSegment, Segment
from leettools.core.schemas.user import User
from leettools.eds.rag.search.filter import BaseCondition, Filter
from leettools.eds.rag.search.searcher_type import SearcherType


class AbstractSearcher(ABC):

    @abstractmethod
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
        Search for segments in the knowledge base.
        """
        pass


def create_searcher_for_kb(
    context: Context,
    searcher_type: SearcherType,
    org: Optional[Org] = None,
    kb: Optional[KnowledgeBase] = None,
) -> AbstractSearcher:
    """
    Get the searcher based on the searcher type.

    We need the kb in some cases to determine the embedder type.
    """
    if searcher_type is None:
        searcher_type = SearcherType.SIMPLE

    if searcher_type == SearcherType.SIMPLE:
        from ._impl.searcher_simple import SearcherSimple

        return SearcherSimple(context)
    elif searcher_type == SearcherType.HYBRID:
        if kb is not None:
            if kb.embedder_type == SegmentEmbedderType.SIMPLE:
                logger().info(
                    f"HYBRID searcher specified for KB {kb.name} with SIMPLE "
                    f"vector embedder. Fall back to SIMPLE searcher."
                )
                from ._impl.searcher_simple import SearcherSimple

                return SearcherSimple(context)

        from ._impl.searcher_hybrid import SearcherHybrid

        return SearcherHybrid(context)
    else:
        raise UnexpectedCaseException(f"Unexpected rerank strategy: {searcher_type}")


@click.command()
@click.option(
    "-q",
    "--query",
    "query",
    required=True,
    help="the question to ask",
)
@click.option(
    "-s",
    "--searcher_type",
    "searcher_type",
    default="simple",
    required=False,
    help="The strategy to use.",
)
@click.option(
    "-k",
    "--kb",
    "kb_name",
    default=None,
    required=False,
    help="The knowledgebase to add the documents to.",
)
def search(query: str, searcher_type: SearcherType, kb_name: str) -> None:
    context = ContextManager().get_context()
    org_manager = context.get_org_manager()
    kb_manager = context.get_kb_manager()
    org = org_manager.get_default_org()

    if kb_name == None:
        kb_name = context.settings.DEFAULT_KNOWLEDGEBASE_NAME
    kb = kb_manager.get_kb_by_name(org, kb_name)
    if kb == None:
        raise ValueError(f"Knowledgebase {kb_name} not found.")

    user = User.get_admin_user()

    searcher = create_searcher_for_kb(
        context=context,
        searcher_type=searcher_type,
        org=org,
        kb=kb,
    )
    top_k = 10
    search_params = None

    filter = Filter(
        relation="and",
        conditions=[
            BaseCondition(
                field=Segment.FIELD_CREATED_TIMESTAMP_IN_MS, operator=">=", value=0
            ),
            BaseCondition(
                field=Segment.FIELD_CREATED_TIMESTAMP_IN_MS,
                operator="<=",
                value=sys.maxsize,
            ),
        ],
    )

    segments = searcher.execute_kb_search(
        org=org,
        kb=kb,
        user=user,
        query=query,
        rewritten_query=query,
        top_k=top_k,
        search_params=search_params,
        query_meta=ChatQueryMetadata(),
        filter=filter,
    )
    dense_vector = 0
    sparse_vector = 0
    common_vector = 0
    for segment in segments:
        if segment.vector_type == "sparse":
            sparse_vector += 1
        elif segment.vector_type == "dense":
            dense_vector += 1
        elif segment.vector_type == "common":
            common_vector += 1
        logger().info("-" * 20)
        logger().info(f"Segment: {segment.segment_uuid}, {segment.search_score}")
        logger().info(f"Vector type: {segment.vector_type}")
        logger().info(f"Content:\n {segment.content}")
        logger().info("-" * 20)
    logger().info(f"Found dense vectors:  {dense_vector}")
    logger().info(f"Found sparse vectors: {sparse_vector}")
    logger().info(f"Found common vectors: {common_vector}")


if __name__ == "__main__":
    EventLogger.set_global_default_level("INFO")
    logger().info("Started searching the vector databases...")
    search()
