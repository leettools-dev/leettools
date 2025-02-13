from typing import List, Optional

from fastapi import Depends, HTTPException

from leettools.common.logging import logger
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.intention import (
    Intention,
    IntentionCreate,
    IntentionUpdate,
)
from leettools.svc.api_router_base import APIRouterBase


class IntentionRouter(APIRouterBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context

        self.intention_store = context.get_intention_store()

        @self.get("/", response_model=List[Intention])
        async def get_all_intentions(
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[Intention]:
            """
            Get intentions based on the category, type, and status.
            """

            return self.intention_store.get_all_intentions()

        @self.get("/{intention_name}", response_model=Optional[Intention])
        async def get_intention_by_name(
            intention_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[Intention]:
            """
            Get a intention by name.
            """
            logger().info(f"Trying to get {intention_name}")

            intention = self.intention_store.get_intention_by_name(intention_name)
            logger().info(f"The intention is: {intention}")
            if intention is None:
                raise HTTPException(
                    status_code=404, detail=f"Intention {intention_name} not found."
                )
            return intention

        @self.put("/", response_model=Intention)
        async def add_intention(
            intention_create: IntentionCreate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Intention:
            """
            Add a intention.
            """

            admin_user = self.auth.get_admin_user()
            if calling_user.user_uuid != admin_user.user_uuid:
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.user_uuid} is not authorized to add intentions",
                )
            return self.intention_store.create_intention(intention_create)

        @self.post("/", response_model=Intention)
        async def update_intention(
            intention_update: IntentionUpdate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Intention:
            """
            Update a intention.
            """

            if calling_user.user_uuid != self.auth.get_admin_user().user_uuid:
                raise HTTPException(
                    status_code=403,
                    detail="User {user.user_uuid} is not authorized to update intentions",
                )
            return self.intention_store.update_intention(intention_update)
