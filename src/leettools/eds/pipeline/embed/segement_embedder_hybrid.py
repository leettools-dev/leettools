import traceback
from typing import List, Optional

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.consts.return_code import ReturnCode
from leettools.core.repo.vector_store import (
    create_vector_store_dense,
    create_vector_store_sparse,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.eds.pipeline.embed.segment_embedder import AbstractSegmentEmbedder
from leettools.eds.str_embedder.dense_embedder import create_dense_embedder_for_kb
from leettools.eds.str_embedder.sparse_embedder import create_sparse_embber_for_kb


class SegmentEmbedderHybrid(AbstractSegmentEmbedder):
    def __init__(
        self, org: Org, kb: KnowledgeBase, user: User, context: Context
    ) -> None:
        """
        Initialize the converter.
        """
        self.org = org
        self.kb = kb
        self.user = user
        self.context = context

        self.dense_vectorstore = create_vector_store_dense(context)
        self.sparse_vectorstore = create_vector_store_sparse(context)

        self.dense_embedder = create_dense_embedder_for_kb(org, kb, user, context)
        self.sparse_embedder = create_sparse_embber_for_kb(org, kb, user, context)

    def _embed(
        self, segments: List[Segment], display_logger: EventLogger
    ) -> ReturnCode:
        rtn_code = ReturnCode.SUCCESS
        if len(segments) == 0:
            display_logger.debug(f"No segments to embed for this run.")
            return rtn_code
        dense_embed_successful = self.dense_vectorstore.save_segments(
            self.org, self.kb, self.user, segments
        )
        if not dense_embed_successful:
            return ReturnCode.FAILURE

        sparse_embed_successful = self.sparse_vectorstore.save_segments(
            self.org, self.kb, self.user, segments
        )

        if not sparse_embed_successful:
            # TODO: should we delete the dense embeddings?
            return ReturnCode.FAILURE

        return ReturnCode.SUCCESS

    def embed_segment_list(
        self, segments: List[Segment], display_logger: Optional[EventLogger] = None
    ) -> ReturnCode:
        if display_logger is None:
            display_logger = logger()

        if segments is None or len(segments) == 0:
            display_logger.info(f"No segments to embed for this run.")
            return ReturnCode.SUCCESS

        try:
            rtn_code = self._embed(segments, display_logger)
            return rtn_code
        except Exception as e:
            trace = traceback.format_exc()
            err_str = f"{trace}"
            if "Please reduce your prompt; or completion length." in err_str:
                display_logger.error(
                    f"Error embedding document [chunk too long]: {trace}"
                )
                return ReturnCode.FAILURE_ABORT
            display_logger.error(f"Error embedding document: {trace}")
            return ReturnCode.FAILURE
