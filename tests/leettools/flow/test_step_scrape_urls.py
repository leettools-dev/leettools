from leettools.chat import chat_utils
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import steps
from leettools.web.web_searcher import WebSearcher


def test_step_scrape_urls_to_docsource():

    temp_setup = TempSetup()
    context = temp_setup.context

    org, kb, user = temp_setup.create_tmp_org_kb_user()

    user = temp_setup.create_tmp_user()

    try:
        _test_flow_step(context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_flow_step(context: Context, org: Org, kb: KnowledgeBase, user: User):

    query = "web design"

    docsource_store = context.get_repo_manager().get_docsource_store()
    new_docsource = docsource_store.create_docsource(
        org=org,
        kb=kb,
        docsource_create=DocSourceCreate(
            kb_id=kb.kb_id,
            source_type=DocSourceType.SEARCH,
            uri=f"search://google?q={query}&date_range=0&max_results=10",
        ),
    )

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org.name,
        kb_name=kb.name,
        username=user.username,
    )

    all_links = {"https://www.yahoo.com/": 1}
    web_searcher = WebSearcher(context)

    list_documents = steps.StepScrpaeUrlsToDocSource.run_step(
        exec_info=exec_info,
        web_searcher=web_searcher,
        links=all_links.keys(),
        docsource=new_docsource,
    )

    assert len(list_documents) == 1

    for url, document in list_documents.items():
        assert url == "https://www.yahoo.com/"
        assert document is not None
        assert document.docsink_uuid is not None
        assert document.document_uuid is not None
