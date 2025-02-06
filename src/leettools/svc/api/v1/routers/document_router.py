from typing import Dict, List, Optional

from fastapi import BackgroundTasks, Depends, HTTPException

from leettools.chat import chat_utils
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.core.schemas.document import Document
from leettools.core.schemas.document_metadata import DocumentSummary
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import iterators
from leettools.flow.exec_info import ExecInfo
from leettools.flow.steps.step_summarize import StepSummarize
from leettools.svc.api_router_base import APIRouterBase


class DocumentRouter(APIRouterBase):

    def _get_org(self, org_name: str) -> Org:
        org = self.org_manager.get_org_by_name(org_name)
        if org is None:
            raise exceptions.EntityNotFoundException(
                entity_name=org_name, entity_type="Org"
            )
        return org

    def _get_kb(self, org_name: str, kb_name: str) -> KnowledgeBase:
        org = self._get_org(org_name)
        kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
        if kb is None:
            raise exceptions.EntityNotFoundException(
                entity_name=kb_name, entity_type="KnowledgeBase"
            )
        return kb

    def _remove_content_from_docs(self, docs: List[Document]) -> List[Document]:
        for doc in docs:
            doc.content = ""
        return docs

    def _summarize_kb_bg_run(
        self,
        org: Org,
        kb: KnowledgeBase,
        force_summarize: bool,
        display_logger: EventLogger,
    ) -> None:
        exec_info = chat_utils.setup_exec_info(
            context=self.context,
            query="",
            org_name=org.name,
            kb_name=kb.name,
            username=None,
            strategy_name=None,
            flow_options={},
            display_logger=display_logger,
        )
        iterators.Summarize.run(
            exec_info=exec_info,
            force_summarize=force_summarize,
        )
        return

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        repo_manager = context.get_repo_manager()
        self.docsource_store = repo_manager.get_docsource_store()
        self.docsink_store = repo_manager.get_docsink_store()
        self.document_store = repo_manager.get_document_store()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.strategy_store = context.get_strategy_store()

        @self.get("/{org_name}", response_model=Dict[str, List[Document]])
        async def get_documents_for_org(
            org_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Return all documents for an org as an dictionary of kb name to documents
            """

            org = self._get_org(org_name)
            results: Dict[str, Document] = {}
            for kb in self.kb_manager.get_all_kbs_for_org(org):
                if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                    continue
                docs = self.document_store.get_documents_for_kb(org, kb)
                results[kb.name] = self._remove_content_from_docs(docs)
            return results

        @self.get("/{org_name}/{kb_name}", response_model=List[Document])
        async def get_documents_for_kb(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Return all documents for a kb
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized to access this KB {kb_name}",
                )
            return self._remove_content_from_docs(
                self.document_store.get_documents_for_kb(org, kb)
            )

        @self.get(
            "/{org_name}/{kb_name}/docsource/{docsource_uuid}",
            response_model=List[Document],
        )
        async def get_document_for_docsource(
            org_name: str,
            kb_name: str,
            docsource_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Return all documents for a docsource
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
                raise exceptions.EntityNotFoundException(
                    entity_name=docsource_uuid, entity_type="DocSource"
                )
            return self._remove_content_from_docs(
                self.document_store.get_documents_for_docsource(org, kb, docsource)
            )

        @self.post(
            "/update_metadata/{org_name}/{kb_name}/{document_uuid}",
            response_model=Document,
        )
        async def update_document_summary(
            org_name: str,
            kb_name: str,
            document_uuid: str,
            doc_summary: DocumentSummary,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Document:
            """
            Manually updatee the summary of a document.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - document_uuid (str): The UUID of the document.
            - doc_summary (DocumentSummary): The document summary set by user.
            - calling_user: The calling user by dependency injection.

            Returns:
            - Document: The updated document.

            Raises:
            - EntityNotFoundException: If the organization, knowledge base, or document is not found.
            """

            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=org_name, entity_type="Organization"
                )

            kb = self.kb_manager.get_kb_by_name(org, kb_name)
            if kb is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            document = self.document_store.get_document_by_id(org, kb, document_uuid)
            if document is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=document_uuid, entity_type="Document"
                )

            document_update = document
            document_update.manual_summary = doc_summary
            updated_document = self.document_store.update_document(
                org, kb, document_update
            )
            return updated_document

        @self.get(
            "/{org_name}/{kb_name}/docsink/{docsink_uuid}",
            response_model=List[Document],
        )
        async def get_document_for_docsink(
            org_name: str,
            kb_name: str,
            docsink_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Return all documents for a docsink
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized to access this KB {kb_name}",
                )
            docsink = self.docsink_store.get_docsink_by_id(org, kb, docsink_uuid)
            if docsink is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=docsink_uuid, entity_type="DocSink"
                )
            return self.document_store.get_documents_for_docsink(org, kb, docsink)

        @self.delete("/{org_name}/{kb_name}/{document_uuid}")
        async def delete_document_by_id(
            org_name: str,
            kb_name: str,
            document_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_write_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized to delete document from this KB {kb_name}",
                )
            doc = self.document_store.get_document_by_id(org, kb, document_uuid)
            if doc is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=document_uuid, entity_type="Document"
                )
            self.document_store.delete_document(org, kb, doc)

        @self.post(
            "/summarize/{org_name}/{kb_name}/{document_uuid}",
            response_model=Optional[Document],
        )
        async def summarize(
            org_name: str,
            kb_name: str,
            document_uuid: str,
            force_summarize: bool = False,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[Document]:
            """
            Summarizes a document based on the given organization, knowledge base,
            and document UUID.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - document_uuid (str): The UUID of the document.
            - force_summarize (bool, optional): Whether to force the document to be
                summarized even if it has already been summarized. Defaults to False.
            - calling_user: The calling user by dependency injection.

            Returns:
            - Document: The updated document after summarization. None if the document
                is not summarized for any reason.

            Raises:
            - EntityNotFoundException: If the organization, knowledge base, or document
                    is not found
            """

            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=org_name, entity_type="Organization"
                )

            kb = self.kb_manager.get_kb_by_name(org, kb_name)
            if kb is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            document = self.document_store.get_document_by_id(org, kb, document_uuid)
            if document is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=document_uuid, entity_type="Document"
                )

            exec_info = ExecInfo(
                context=context,
                org=org,
                kb=kb,
                user=calling_user,
                target_chat_query_item=None,
                display_logger=None,
            )

            all_links = {}

            updated_document = StepSummarize.run_step(
                exec_info=exec_info,
                document=document,
                all_links=all_links,
                force_summarize=force_summarize,
            )

            return updated_document

        @self.post("/summarize_kb/{org_name}/{kb_name}")
        async def summarize_kb(
            org_name: str,
            kb_name: str,
            background_tasks: BackgroundTasks,
            force_summarize: bool = False,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> None:
            """
            Summarizes a knowledge base (KB) for a given organization. This is a best
            effort operation and run a backeng task. It may take some time to complete
            and does not guarantee that all documents will be summarized.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - force_summarize (bool, optional): Flag indicating whether to force the
                    summarization process. Defaults to False.
            - calling_user: The calling user by dependency injection.

            Raises:
            - EntityNotFoundException: If the organization or knowledge base is not found.
            - HTTPException: If the user is not authorized to access the knowledge base.

            Returns:
            - None
            """

            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=org_name, entity_type="Organization"
                )

            kb = self.kb_manager.get_kb_by_name(org, kb_name)
            if kb is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if self.auth.can_read_kb(org=org, kb=kb, user=calling_user) == False:
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not authorized toaccess this KB {kb_name}",
                )

            display_logger = logger()
            background_tasks.add_task(
                self._summarize_kb_bg_run, org, kb, force_summarize, display_logger
            )
            return
