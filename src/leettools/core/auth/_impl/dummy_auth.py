from typing import Any, Dict

from fastapi import HTTPException, Request

from leettools.core.auth.authorizer import AbstractAuthorizer
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.core.user.user_store import AbstractUserStore
from leettools.settings import SystemSettings


class DummyAuth(AbstractAuthorizer):
    """
    A dummy authorizer that implements the API but does not check for user permissions.
    """

    def __init__(self, settings: SystemSettings, user_store: AbstractUserStore):
        super().__init__(settings, user_store)
        self.admin_user = self.user_store.get_user_by_name(User.ADMIN_USERNAME)
        if self.admin_user is None:
            raise HTTPException(
                status_code=500, detail=f"Admin user {User.ADMIN_USERNAME} not found"
            )

    def get_admin_user(self) -> User:
        return self.admin_user

    def get_user_from_request(self, request: Request) -> User:
        user_name = request.headers.get("username")
        if user_name is None or user_name == "":
            return self.admin_user
        user = self.user_store.get_user_by_name(user_name)
        if user is None:
            raise HTTPException(status_code=404, detail=f"User {user_name} not found")
        return user

    def get_user_from_payload(self, user_dict: Dict[str, Any]) -> User:
        user_name = user_dict.get("username")
        if user_name is None or user_name == "":
            return self.admin_user
        user = self.user_store.get_user_by_name(user_name)
        if user is None:
            raise HTTPException(status_code=404, detail=f"User {user_name} not found")
        return user

    def can_read_org(self, org: Org, user: User) -> bool:
        return True

    def can_read_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        return True

    def can_write_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        return True

    def can_share_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        return True

    def can_unshare_kb(self, org: Org, kb: KnowledgeBase, user: User) -> bool:
        return True

    def _reset_for_test(self) -> None:
        from leettools.context_manager import ContextManager

        context = ContextManager().get_context()
        self.settings = context.settings
        self.user_store = context.get_user_store()
        self.admin_user = self.user_store.get_user_by_name(User.ADMIN_USERNAME)
