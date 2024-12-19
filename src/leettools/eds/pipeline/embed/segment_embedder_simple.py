import traceback
from typing import List, Optional

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.consts.return_code import ReturnCode
from leettools.core.repo.vector_store import create_vector_store_dense
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.eds.pipeline.embed.segment_embedder import AbstractSegmentEmbedder


class SegmentEmbedderSimple(AbstractSegmentEmbedder):
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
        self.log_location: str = None

    def _embed(
        self,
        segments: List[Segment],
        display_logger: EventLogger,
    ) -> ReturnCode:
        if len(segments) == 0:
            display_logger.info(f"No segments to embed for this run.")
            return ReturnCode.SUCCESS

        doc_id = segments[0].document_uuid
        op_success = self.dense_vectorstore.save_segments(
            org=self.org,
            kb=self.kb,
            user=self.user,
            segments=segments,
        )
        if op_success:
            display_logger.info(f"Successfully embed segments for document {doc_id}")
            return ReturnCode.SUCCESS
        else:
            return ReturnCode.FAILURE

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
            display_logger.error(f"Error embedding document: {trace}")
            return ReturnCode.FAILURE
