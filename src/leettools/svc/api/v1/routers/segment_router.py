from typing import List

from fastapi import Depends

from leettools.common.exceptions import EntityNotFoundException
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.svc.api_router_base import APIRouterBase


class SegmentRouter(APIRouterBase):

    def _get_org(self, org_name: str) -> Org:
        org = self.org_manager.get_org_by_name(org_name)
        if org is None:
            raise EntityNotFoundException(entity_name=org_name, entity_type="Org")
        return org

    def _get_kb(self, org_name: str, kb_name: str) -> KnowledgeBase:
        org = self._get_org(org_name)
        kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
        if kb is None:
            raise EntityNotFoundException(
                entity_name=kb_name, entity_type="KnowledgeBase"
            )
        return kb

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        repo_manager = context.get_repo_manager()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.segment_store = repo_manager.get_segment_store()

        @self.get("/{org_name}/{kb_name}/{document_uuid}", response_model=List[Segment])
        async def get_segments_for_document(
            org_name: str,
            kb_name: str,
            document_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Return all documents for an org as an dictionary of kb name to documents
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            return self.segment_store.get_all_segments_for_document(
                org, kb, document_uuid
            )
