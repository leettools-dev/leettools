from fastapi import APIRouter

from leettools.context_manager import ContextManager
from leettools.core.auth.authorizer import AbstractAuthorizer


class APIRouterBase(APIRouter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = ContextManager().get_context()
        self.context = context
        self.settings = context.settings
        self.auth: AbstractAuthorizer = context.get_authorizer()
