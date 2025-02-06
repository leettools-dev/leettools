from typing import Optional

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from leettools.common.exceptions import EntityNotFoundException
from leettools.common.logging import logger
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.svc.api_router_base import APIRouterBase


class MDRouter(APIRouterBase):

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
        self.doc_store = context.get_repo_manager().get_document_store()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()

        @self.get("/")
        async def read_document(
            org_name: str,
            kb_name: str,
            doc_uuid: str,
            start_offset: Optional[int] = None,
            end_offset: Optional[int] = None,
            format: str = Query("json", enum=["json", "html"]),
        ):
            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            doc: Document = self.doc_store.get_document_by_id(org, kb, doc_uuid)
            if doc is None:
                raise HTTPException(status_code=404, detail="Document not found")

            content = doc.content

            start_marker = "(((#start#]]]"
            end_marker = "(((#end#]]]"
            if (
                start_offset is not None
                and end_offset is not None
                and 0 <= start_offset < end_offset <= len(content)
            ):
                highlighted_content = (
                    start_marker + content[start_offset:end_offset] + end_marker
                )
                logger().debug(f"highlighted_content: {highlighted_content}")
                full_content = (
                    content[:start_offset] + highlighted_content + content[end_offset:]
                )
            else:
                logger().debug("offsets not correct, using full content.")
                full_content = content

            lexer = get_lexer_by_name("md")
            formatter = HtmlFormatter(full=True, style="friendly")
            html_content: str = highlight(full_content, lexer, formatter)
            html_content = html_content.replace(
                start_marker, "<div id='highlights' style='background-color: #FFFFE0'>"
            )
            html_content = html_content.replace(end_marker, "</div>")

            if format == "html":
                return HTMLResponse(content=html_content)
            else:
                return JSONResponse(content={"html_content": html_content})
