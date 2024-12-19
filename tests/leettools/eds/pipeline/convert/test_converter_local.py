""" Tests for the ConverterLocal class. """

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.docsink import DocSink, DocSinkCreate, DocSinkInDB
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.pipeline.convert.converter import create_converter


def test_converter_local(tmp_path):

    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_function(tmp_path, context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(tmp_path, context: Context, org: Org, kb: KnowledgeBase):

    file_path = tmp_path / "test.html"
    file_path.write_text(
        """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>My First Heading here</h1>
        <p>My first paragraph here.</p>
    </body>
    </html>
    """,
        encoding="utf8",
    )

    repo_manager = context.get_repo_manager()
    kb_id = kb.kb_id

    docstore = repo_manager.get_document_store()
    docsink_create = DocSinkCreate(
        docsource_uuid="source1",
        kb_id=kb_id,
        original_doc_uri="http://example.com/test.html",
        raw_doc_uri=str(file_path),
    )
    docsink_in_db = DocSinkInDB.from_docsink_create(docsink_create)
    docsink_in_db.docsink_uuid = "12345"
    docsink = DocSink.from_docsink_in_db(docsink_in_db)

    file_loader = create_converter(
        org=org,
        kb=kb,
        docsink=docsink,
        docstore=docstore,
        settings=context.settings,
    )
    file_loader.set_log_location(str(tmp_path) + "/test.log")

    rtn_code = file_loader.convert()
    assert rtn_code == ReturnCode.SUCCESS
