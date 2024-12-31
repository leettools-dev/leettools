from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context, ContextManager
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.document import DocumentCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.pipeline.split.splitter import Splitter


def test_splitter():
    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    kb_id = kb.kb_id

    repo_manager = context.get_repo_manager()
    docstore = repo_manager.get_document_store()

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

    docsource_store = repo_manager.get_docsource_store()
    docsource_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb_id,
        source_type=DocSourceType.URL,
        uri="http://www.test1.com",
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)

    docsink_store = repo_manager.get_docsink_store()
    docsink_create = DocSinkCreate(
        docsource=docsource,
        original_doc_uri="http://www.test1.com",
        raw_doc_uri="/tmp/test1.html",
    )
    docsink = docsink_store.create_docsink(org, kb, docsink_create)
    doc_uri = "uri1"

    document_create = DocumentCreate(
        docsink=docsink,
        content=md_content,
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
