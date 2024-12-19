from typing import Set

from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment


class NeighboringExtension:
    def __init__(self, context: Context) -> None:
        repo_manager = context.get_repo_manager()
        self.segstore = repo_manager.get_segment_store()

    def get_neighboring_context(
        self,
        org: Org,
        kb: KnowledgeBase,
        segment: Segment,
        segments_set: Set[str] = set(),
    ) -> str:
        """
        Get the neighboring context for a segment.
        """
        rtn_text = ""
        parent_segment = self.segstore.get_parent_segment(org, kb, segment)
        if (
            parent_segment is not None
            and parent_segment.segment_uuid not in segments_set
        ):
            segments_set.add(parent_segment.segment_uuid)
            rtn_text += parent_segment.content + "\n\n"

        older_sibling = self.segstore.get_older_sibling_segment(org, kb, segment)
        if older_sibling is not None and older_sibling.segment_uuid not in segments_set:
            segments_set.add(older_sibling.segment_uuid)
            rtn_text += older_sibling.content + "\n\n"
        rtn_text += segment.content + "\n\n"

        younger_sibling = self.segstore.get_younger_sibling_segment(org, kb, segment)
        if (
            younger_sibling is not None
            and younger_sibling.segment_uuid not in segments_set
        ):
            segments_set.add(younger_sibling.segment_uuid)
            rtn_text += younger_sibling.content + "\n\n"
        return rtn_text
