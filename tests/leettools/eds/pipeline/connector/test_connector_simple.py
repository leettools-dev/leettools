""" Test the IngesterSimple class """

import pytest

from leettools.common.temp_setup import TempSetup
from leettools.common.utils.file_utils import uri_to_path
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.pipeline.ingest.connector import create_connector


def test_uri_to_path():
    uri = "file:///tmp/test"
    path = uri_to_path(uri)
    assert path.as_uri() == uri
    assert str(path) == "/tmp/test"

    uri = "/tmp/test"
    path = uri_to_path(uri)
    assert path.as_uri() == f"file://{uri}"
    assert str(path) == "/tmp/test"


def test_connector_simple():
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_connector_simple(context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_connector_simple(context: Context, org: Org, kb: KnowledgeBase):
    settings = context.settings
    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()

    kb_id = kb.kb_id
    url = "https://www.example.com/"
    docsource_create = DocSourceCreate(
        source_type=DocSourceType.WEB,
        kb_id=kb_id,
        uri=url,
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)

    connector = create_connector(
        context, "connector_simple", org, kb, docsource, docsink_store
    )
    rtn_code = connector.ingest()
    assert rtn_code == ReturnCode.SUCCESS

    rtn_list = connector.get_ingested_docsink_list()
    assert len(rtn_list) == 1


def test_file_copy(tmp_path):
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_file_copy(tmp_path, context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_file_copy(tmp_path, context: Context, org: Org, kb: KnowledgeBase):
    kb_id = kb.kb_id

    settings = context.settings
    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()

    filepath = f"{str(tmp_path)}/test.html"
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Test</h1></body></html>")
    filepath = f"{str(tmp_path)}/test1.html"
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Test</h1></body></html>")

    docsource_create = DocSourceCreate(
        uri=str(tmp_path),
        kb_id=kb_id,
        source_type=DocSourceType.FILE,
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)
    connector = create_connector(
        context, "connector_simple", org, kb, docsource, docsink_store
    )
    rtn_code = connector.ingest()
    rtn_list = connector.get_ingested_docsink_list()

    assert rtn_code == ReturnCode.SUCCESS
    assert len(rtn_list) == 2


def test_local_file(tmp_path):
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_local_file(tmp_path, context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_local_file(tmp_path, context: Context, org: Org, kb: KnowledgeBase):
    kb_id = kb.kb_id

    settings = context.settings
    docsource_store = context.get_repo_manager().get_docsource_store()
    docsink_store = context.get_repo_manager().get_docsink_store()

    filepath = f"{str(tmp_path)}/test.txt"
    with open(filepath, "w") as f:
        f.write("html body h1 Test h1 body html")
    filepath = f"{str(tmp_path)}/test1.txt"
    with open(filepath, "w") as f:
        f.write("html body h1 Test h1 body html")
    docsource_create = DocSourceCreate(
        uri=str(tmp_path),
        kb_id=kb_id,
        source_type=DocSourceType.LOCAL,
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)
    connector = create_connector(
        context, "connector_simple", org, kb, docsource, docsink_store
    )
    rtn_code = connector.ingest()
    rtn_list = connector.get_ingested_docsink_list()

    assert rtn_code == ReturnCode.SUCCESS
    assert len(rtn_list) == 2


if __name__ == "__main__":
    pytest.main()
