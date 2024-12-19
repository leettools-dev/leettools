from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.document import DocumentCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.pipeline.split.splitter import Splitter


def test_splitter():
    """Test the traverse_hierarchy method."""
    context = ContextManager().get_context()  # type: Context

    temp_setup = TempSetup()
    org, kb, user = temp_setup.create_tmp_org_kb_user()

    try:
        _test_function(context, org, kb)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    kb_id = kb.kb_id

    repo_manager = context.get_repo_manager()
    docstore = repo_manager.get_document_store()
    segstore = repo_manager.get_segment_store()
    graphstore = repo_manager.get_docgraph_store()

    md_content = """
        # section 1
        1. differ materially from those in the forward-looking statements, including, without limitation, the risks set forth in Part I, Item 1A, “Risk Factors” of the Annual Report on Form 10-K for the fiscal year ended December 31, 2022 and that are otherwise described or updated from time to time in our other filings with the Securities and 
        2. differ materially from those in the forward-looking statements, including, without limitation, the risks set forth in Part I, Item 1A, “Risk Factors” of the Annual Report on Form 10-K for the fiscal year ended December 31, 2022 and that are otherwise described or updated from time to time in our other filings with the Securities and 

        Consolidated Balance Sheets (in millions, except per share data) (unaudited)
        something here
        |  | September 30, 2023 | December 31, 2022
        | --- | --- | ---
        | Assets
        | Current assets Cash and cash equivalents | $ 15,932 | $ 16,253
        | Short-term investments | 10,145 | 5,932
        | Accounts receivable, net | 2,520 | 2,952
        | Inventory | 13,721 | 12,839
        | Prepaid expenses and other current assets | 2,708 | 2,941
        Based on our estimation, it is the best time to invest in the stock market.
    """

    docsink_uuid = "12345"
    docsource_uuid = "12345"
    doc_uri = "uri1"

    document_create = DocumentCreate(
        content=md_content,
        docsink_uuid=docsink_uuid,
        docsource_uuid=docsource_uuid,
        kb_id=kb_id,
        doc_uri=doc_uri,
    )
    document = docstore.create_document(org, kb, document_create)
    splitter = Splitter(
        context=context,
        org=org,
        kb=kb,
    )
    rtn_code = splitter.split(doc=document)
    assert rtn_code == ReturnCode.SUCCESS
