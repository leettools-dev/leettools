from typing import List

from fastapi.testclient import TestClient

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.scheduler.schemas.program import (
    ConnectorProgramSpec,
    ProgramSpec,
    ProgramType,
    ProgramTypeDescrtion,
)
from leettools.eds.scheduler.schemas.task import Task, TaskCreate, TaskStatusDescription
from leettools.svc.api.v1.routers.task_router import TaskRouter


def test_task_router():

    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    router = TaskRouter()
    client = TestClient(router)

    try:
        _test_router(client, context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_router(
    client: TestClient, context: Context, org: Org, kb: KnowledgeBase, user: User
) -> None:

    task_manager = context.get_task_manager()
    task_store = task_manager.get_taskstore()

    docsource_store = context.get_repo_manager().get_docsource_store()

    docsource = docsource_store.create_docsource(
        org,
        kb,
        DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.LOCAL,
            uri="dummyuri",
            display_name="test doc source",
        ),
    )

    # Test get_program_types
    headers = {"username": user.username}

    response = client.get(f"/program_types", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    program_type_descriptions = []
    for program_type_json in response.json():
        program_type_descriptions.append(
            ProgramTypeDescrtion.model_validate(program_type_json)
        )
    assert len(program_type_descriptions) == 5

    # Test get_task_status_types
    response = client.get(f"/status_types", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    task_status_types = []
    for task_status_json in response.json():
        task_status_types.append(TaskStatusDescription.model_validate(task_status_json))
    assert len(task_status_types) == len(Task.get_task_status_descriptions())

    program_spec = ProgramSpec(
        program_type=ProgramType.CONNECTOR,
        real_program_spec=ConnectorProgramSpec(
            org_id=org.org_id, kb_id=kb.kb_id, source=docsource
        ),
    )

    task = task_store.create_task(
        TaskCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            docsource_uuid=docsource.docsource_uuid,
            program_spec=program_spec,
        )
    )

    response = client.get(f"/list/{org.name}/{kb.name}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    result_list: List[Task] = []
    for task_json in response.json():
        result_list.append(Task.model_validate(task_json))
    assert len(result_list) == 1
    assert result_list[0].org_id == org.org_id
    assert result_list[0].kb_id == kb.kb_id
    assert result_list[0].docsource_uuid == docsource.docsource_uuid
    assert result_list[0].program_spec.program_type == program_spec.program_type
    assert (
        result_list[0].program_spec.real_program_spec.org_id
        == program_spec.real_program_spec.org_id
    )
    assert (
        result_list[0].program_spec.real_program_spec.kb_id
        == program_spec.real_program_spec.kb_id
    )
    assert (
        result_list[0].program_spec.real_program_spec.source.docsource_uuid
        == docsource.docsource_uuid
    )
    assert result_list[0].task_uuid == task.task_uuid
