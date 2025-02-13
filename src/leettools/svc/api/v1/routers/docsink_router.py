from typing import Dict, List

from fastapi import Depends, HTTPException

from leettools.common.exceptions import EntityNotFoundException
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.svc.api_router_base import APIRouterBase


class DocSinkRouter(APIRouterBase):

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
        self.docsink_store = repo_manager.get_docsink_store()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()

        @self.get("/{org_name}", response_model=Dict[str, List[DocSink]])
        async def get_docsinks_for_org(
            org_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Dict[str, List[DocSink]]:
            """
            Retrieves the document sinks for a given organization.

            Args:
            - org_name (str): The name of the organization.
            - calling_user: The calling user by dependency injection.

            Returns:
            - dict: A dictionary containing the document sinks for each knowledge
                      base in the organization.
            """

            org = self._get_org(org_name)
            results: Dict[str, List[DocSink]] = {}
            for kb in self.kb_manager.get_all_kbs_for_org(org):
                if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                    continue
                docsinks = self.docsink_store.get_docsinks_for_kb(org, kb)
                results[kb.name] = docsinks
            return results

        @self.get("/{org_name}/{kb_name}", response_model=List[DocSink])
        async def get_docsinks_for_kb(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[DocSink]:
            """
            Get all docsinks for a kb

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[Docsink]: A list of docsinks for the specified knowledge base.

            Raises:
            - HTTPException: If the user is not authorized to access the knowledge base.
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized to access this KB {kb_name}",
                )
            return self.docsink_store.get_docsinks_for_kb(org, kb)

        @self.get(
            "/{org_name}/{kb_name}/{docsource_uuid}",
            response_model=List[DocSink],
        )
        async def get_docsinks_for_docsource(
            org_name: str,
            kb_name: str,
            docsource_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[DocSink]:
            """
            Get all docsinks for a docsource

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - docsource_uuid (str): The UUID of the docsource.
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[Docsink]: A list of docsinks associated with the docsource.

            Raises:
            - HTTPException: If the user is not authorized to access the knowledge base.
            - EntityNotFoundException: If the docsource is not found.
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized to access this KB {kb_name}",
                )

            docsource = self.docsource_store.get_docsource(org, kb, docsource_uuid)
            if docsource is None:
                raise EntityNotFoundException(
                    entity_name=docsource_uuid, entity_type="DocSource"
                )
            docsinks = self.docsink_store.get_docsinks_for_docsource(org, kb, docsource)
            return docsinks

        @self.delete("/{org_name}/{kb_name}/{docsource_uuid}/{docsink_uuid}")
        async def delete_docsink_by_id(
            org_name: str,
            kb_name: str,
            docsource_uuid: str,
            docsink_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> None:
            """
            Delete a DocSink by its ID.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - docsource_uuid (str): The UUID of the DocSource.
            - docsink_uuid (str): The UUID of the DocSink.
            - calling_user: The calling user by dependency injection.

            Raises:
            - HTTPException: If the user is not authorized to access the knowledge base.
            - HTTPException: If the DocSink does not belong to the DocSource.
            - EntityNotFoundException: If the DocSink with the given ID is not found.

            Returns:
            - None
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_write_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized to access this KB {kb_name}",
                )

            docsink = self.docsink_store.get_docsink_by_id(org, kb, docsink_uuid)
            if docsink is None:
                raise EntityNotFoundException(
                    entity_name=docsink_uuid, entity_type="DocSink"
                )

            if docsource_uuid not in docsink.docsource_uuids:
                raise HTTPException(
                    status_code=400,
                    detail=f"DocSink {docsink_uuid} does not belong to DocSource {docsource_uuid}",
                )

            self.docsink_store.delete_docsink(org, kb, docsink)
