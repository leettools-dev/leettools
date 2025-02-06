from typing import List

from fastapi import HTTPException

from leettools.common.exceptions import EntityNotFoundException
from leettools.core.schemas.organization import Org
from leettools.svc.api_router_base import APIRouterBase


class OrgRouter(APIRouterBase):

    def _get_org(self, org_name: str):
        org = self.org_manager.get_org_by_name(org_name)
        if org is None:
            raise EntityNotFoundException(entity_name=org_name, entity_type="Org")
        return org

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        self.org_manager = context.get_org_manager()

        @self.get("/default", response_model=Org)
        async def get_default() -> Org:
            return self.org_manager.get_default_org()

        @self.get("/{org_name}", response_model=Org)
        async def get(org_name: str) -> Org:
            try:
                org = self._get_org(org_name)
                return org
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.get("/", response_model=List[Org])
        async def get_all() -> List[Org]:
            try:
                orgs = self.org_manager.list_orgs()
                return orgs
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
