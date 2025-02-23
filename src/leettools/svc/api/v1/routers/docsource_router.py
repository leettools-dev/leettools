from typing import Dict, List

from fastapi import Depends, HTTPException

from leettools.common import exceptions
from leettools.common.exceptions import EntityNotFoundException
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSource, DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow.utils import pipeline_utils
from leettools.svc.api_router_base import APIRouterBase


class DocSourceRouter(APIRouterBase):

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
        self.docsource_store = repo_manager.get_docsource_store()
        self.docksink_store = repo_manager.get_docsink_store()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()

        @self.get("/types", response_model=List[DocSourceType])
        async def get_docsource_types():
            """
            Get all docsource types
            """
            return list(DocSourceType)

        @self.get("/{org_name}", response_model=Dict[str, List[DocSource]])
        async def get_docsources_for_org(
            org_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Get all docsources for an org
            """

            org = self._get_org(org_name)
            docsources: Dict[KnowledgeBase, List[DocSource]] = {}
            for kb in self.kb_manager.get_all_kbs_for_org(org):
                if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                    continue
                docsources[kb.name] = self.docsource_store.get_docsources_for_kb(
                    org, kb
                )
            return docsources

        @self.get("/{org_name}/{kb_name}", response_model=List[DocSource])
        async def get_docsources_for_kb(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Get all docsources for a knowledgebase
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized to access this KB {kb_name}",
                )
            docsources = self.docsource_store.get_docsources_for_kb(org, kb)
            return docsources

        @self.get("/{org_name}/{kb_name}/{docsource_uuid}", response_model=DocSource)
        async def get_docsource_by_id(
            org_name: str,
            kb_name: str,
            docsource_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> DocSource:
            """
            Get docsource by uuid
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )
            docsource = self.docsource_store.get_docsource(
                org,
                kb,
                docsource_uuid,
            )
            return docsource

        @self.post("/{org_name}/{kb_name}/{docsource_uuid}", response_model=DocSource)
        async def ingest_docsource_by_id(
            org_name: str,
            kb_name: str,
            docsource_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> DocSource:
            """
            Get docsource by uuid
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )
            docsource = self.docsource_store.get_docsource(
                org,
                kb,
                docsource_uuid,
            )
            if docsource is None:
                raise exceptions.ParametersValidationException(
                    [
                        f"Docsource {docsource_uuid} not found in Org {org.name}, KB {kb.name}"
                    ]
                )
            display_logger = logger()
            docsource.docsource_status = DocSourceStatus.CREATED
            docsource.updated_at = time_utils.current_datetime()
            self.docsource_store.update_docsource(org, kb, docsource)

            if kb.auto_schedule and self.context.is_svc:
                updated_docsrc = pipeline_utils.process_docsources_auto(
                    org=org,
                    kb=kb,
                    docsources=[docsource],
                    context=context,
                    display_logger=display_logger,
                )
            else:
                updated_docsrc = pipeline_utils.process_docsource_manual(
                    org=org,
                    kb=kb,
                    user=calling_user,
                    docsource=docsource,
                    context=context,
                    display_logger=display_logger,
                )
            if len(updated_docsrc) != 1:
                raise exceptions.UnexpectedCaseException(
                    f"Expected 1 docsource to be updated, got {len(updated_docsrc)}"
                )
            return updated_docsrc[0]

        @self.post("/{org_name}/{kb_name}", response_model=DocSource)
        async def add_docsource(
            org_name: str,
            kb_name: str,
            docsource_create: DocSourceCreate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Add a docsource
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_write_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toadd this KB {kb_name}",
                )
            docsource = self.docsource_store.create_docsource(org, kb, docsource_create)
            return docsource

        @self.delete("/{org_name}/{kb_name}")
        async def delete_docsource(
            org_name: str,
            kb_name: str,
            docsource: DocSource,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Delete a docsource
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_write_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized todelete docsource "
                    f"in this KB {kb_name}",
                )
            self.docsource_store.delete_docsource(org, kb, docsource)
