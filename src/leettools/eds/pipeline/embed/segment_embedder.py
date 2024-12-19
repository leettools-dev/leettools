from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.consts.return_code import ReturnCode
from leettools.core.consts.segment_embedder_type import SegmentEmbedderType
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User


class AbstractSegmentEmbedder(ABC):
    @abstractmethod
    def embed_segment_list(
        self, segments: List[Segment], display_logger: Optional[EventLogger] = None
    ) -> ReturnCode:
        """
        Embed the segment content and save it to vectorstore.

        Args:
        -  segments: List of segments to embed
        -  display_logger: Optional logger to log the embedding process

        Returns:
        -  bool: True if segment embedding is successfully saved, False otherwise
        """
        pass


def create_segment_embedder_for_kb(
    org: Org, kb: KnowledgeBase, user: User, context: Context
) -> AbstractSegmentEmbedder:
    """
    Factory function to create a segment embedder based on the KB config.

    Args:
    - org: The organization.
    - kb: The knowledge base.
    - user: The user.
    - context: The context.

    Returns:
    - An embedder for the knowledge base.
    """
    if kb.embedder_type == SegmentEmbedderType.SIMPLE:
        from .segment_embedder_simple import SegmentEmbedderSimple

        return SegmentEmbedderSimple(org, kb, user, context)
    elif kb.embedder_type == SegmentEmbedderType.HYBRID:
        from .segement_embedder_hybrid import SegmentEmbedderHybrid

        return SegmentEmbedderHybrid(org, kb, user, context)
    else:
        raise exceptions.UnexpectedCaseException(
            f"Unexpected vector embedder type: {kb.embedder_type}"
        )
