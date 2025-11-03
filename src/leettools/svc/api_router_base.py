from fastapi import APIRouter, Request

from leettools.common.logging import logger
from leettools.context_manager import ContextManager
from leettools.core.auth.authorizer import AbstractAuthorizer


class APIRouterBase(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = ContextManager().get_context()
        self.context = context
        self.settings = context.settings
        self.auth: AbstractAuthorizer = context.get_authorizer()

    async def get_locale(self, request: Request) -> str:
        default_lang = self.settings.DEFAULT_LANGUAGE
        lang = request.headers.get("accept-language", None)
        if lang is None:
            lang = request.headers.get("Accept-Language", default_lang)
        lang = lang.split(",")[0]
        logger().noop(
            f"[DependencyInjection]get_locale accept-language: {lang}", noop_lvl=2
        )
        return lang
