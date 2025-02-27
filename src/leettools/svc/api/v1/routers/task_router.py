from typing import List

from fastapi import Depends, HTTPException

from leettools.common.exceptions import EntityNotFoundException
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.scheduler.schemas.program import (
    EmbedProgramSpec,
    ProgramSpec,
    ProgramType,
    ProgramTypeDescrtion,
    SplitProgramSpec,
)
from leettools.eds.scheduler.schemas.task import Task, TaskStatusDescription
from leettools.svc.api_router_base import APIRouterBase


class TaskRouter(APIRouterBase):

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

    def _remove_content_from_spec(self, task: Task) -> Task:
        # Remove content from the source of the task to avoid sending it over the wire
        if task.program_spec.program_type == ProgramType.SPLIT:
            spec: SplitProgramSpec = task.program_spec.real_program_spec
            doc: Document = spec.source
            doc.content = ""
        elif task.program_spec.program_type == ProgramType.EMBED:
            spec: EmbedProgramSpec = task.program_spec.real_program_spec
            # for segment in spec.source:
            #    segment.content = ""
            spec.source = []
        return task

    def _remove_content_from_tasks(self, tasks: List[Task]) -> List[Task]:
        rtn_tasks = []
        for task in tasks:
            rtn_tasks.append(self._remove_content_from_spec(task))
        return rtn_tasks

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        task_manager = context.get_task_manager()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.task_store = task_manager.get_taskstore()

        @self.get("/program_types", response_model=List[ProgramTypeDescrtion])
        async def get_program_types():
            """
            Get all program types
            """
            return ProgramSpec.get_program_type_descriptions()

        @self.get("/status_types", response_model=List[TaskStatusDescription])
        async def get_task_status_types():
            """
            Get all task statuses
            """
            return Task.get_task_status_descriptions()

        @self.get("/list/{org_name}", response_model=List[Task])
        async def get_tasks_for_org(
            org_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[Task]:
            """
            Get all tasks for an organization.

            Args:
            - org_name: The name of the organization
            - calling_user: The current user from the dependency injection

            Returns:
            - List[Task]: A list of tasks for the organization
            """
            org = self._get_org(org_name)
            if not self.auth.can_read_org(org=org, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} does not have permission to read org {org_name}",
                )
            tasks = self.task_store.get_all_tasks_for_org(org)
            return self._remove_content_from_tasks(tasks)

        @self.get("/list/{org_name}/{kb_name}", response_model=List[Task])
        async def get_tasks_for_kb(
            org_name: str,
            kb_name: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[Task]:
            """
            Get all tasks for a knowledgebase.

            Args:
            - org_name: The name of the organization
            - kb_name: The name of the knowledgebase
            - calling_user: The current user from the dependency injection

            Returns:
            - List[Task]: A list of tasks for the knowledgebase
            """

            org = self._get_org(org_name)
            kb = self._get_kb(org_name, kb_name)
            if not self.auth.can_read_kb(org=org, kb=kb, user=calling_user):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} does not have permission to read kb {kb_name}",
                )
            tasks = self.task_store.get_all_tasks_for_kb(org, kb)
            return self._remove_content_from_tasks(tasks)

        @self.get("/docsource/{docsource_uuid}", response_model=List[Task])
        async def get_tasks_for_docsource(
            docsource_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Get all tasks for a docsource
            """

            tasks = self.task_store.get_tasks_for_docsource(docsource_uuid)
            return self._remove_content_from_tasks(tasks)

        @self.get("/docsink/{docsink_uuid}", response_model=List[Task])
        async def get_tasks_for_docsink(
            docsink_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Get all tasks for a docsink
            """

            tasks = self.task_store.get_tasks_for_docsink(docsink_uuid)
            return self._remove_content_from_tasks(tasks)

        @self.get("/document/{doc_uuid}", response_model=List[Task])
        async def get_tasks_for_document(
            doc_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Get all tasks for a document
            """

            tasks = self.task_store.get_tasks_for_document(doc_uuid)
            return self._remove_content_from_tasks(tasks)

        @self.get("/{task_uuid}", response_model=Task)
        async def get_task_by_id(
            task_uuid: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Get a task by task_uuid
            """

            task = self.task_store.get_task_by_uuid(task_uuid)
            if task is None:
                raise HTTPException(
                    status_code=404, detail=f"Task {task_uuid} not found"
                )
            return task
