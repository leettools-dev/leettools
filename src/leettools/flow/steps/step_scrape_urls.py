from typing import ClassVar, Dict, List, Type

from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep
from leettools.flow.utils import pipeline_utils
from leettools.web.web_searcher import WebSearcher


class StepScrpaeUrlsToDocSource(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "scrape_urls_to_docsource"

    @classmethod
    def short_description(cls) -> str:
        return "Scrape the specified URLs to the target DocSource."

    @classmethod
    def full_description(cls) -> str:
        return """Given a web searcher, a list of URLs, and a DocSource, scrape the URLs
and save them as a list of DocSinks in the DocSource.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [WebSearcher]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return []

    @staticmethod
    def run_step(
        exec_info: ExecInfo,
        web_searcher: WebSearcher,
        links: List[str],
        docsource: DocSource,
    ) -> Dict[str, Document]:
        """
        Scrape the URLs and create documents for an existing docsource.

        If we want to scrape a web site and create documents for a new docsource, we
        should just create a new docsource with type WEB.

        Right now, we do not support a docsource corresponding to a list of URLs.

        Args:
        - exec_info: Execution information
        - web_searcher: The WebSearcher instance to use
        - links: The list of urls to scrape with format
        - docsource: The document source to create documents for

        Returns:
        - Dict[str, Docoumnet]: The documents created successfully, the key is the url.
        """
        context = exec_info.context
        docsink_store = context.get_repo_manager().get_docsink_store()
        docsource_store = context.get_repo_manager().get_docsource_store()
        document_store = context.get_repo_manager().get_document_store()
        display_logger = exec_info.display_logger
        org = exec_info.org
        kb = exec_info.kb
        query = exec_info.target_chat_query_item.query_content

        display_logger.info(f"[Status]Scraping {len(links)} URLs.")

        docsink_create_list = web_searcher.scrape_urls_to_docsinks(
            query=query,
            org=org,
            kb=kb,
            docsource=docsource,
            links=links,
            display_logger=display_logger,
        )

        docsinks: List[DocSink] = []
        for docsink_create in docsink_create_list:
            docsink = docsink_store.create_docsink(org, kb, docsink_create)
            docsinks.append(docsink)

        successful_documents: Dict[str, Document] = {}
        if kb.auto_schedule == True:
            pipeline_utils.process_docsources_auto(
                org=org,
                kb=kb,
                docsources=[docsource],
                context=context,
                display_logger=display_logger,
            )
            for docsink in docsinks:
                try:
                    documents = document_store.get_documents_for_docsink(
                        org, kb, docsink
                    )
                    if documents is None:
                        continue
                    if len(documents) > 1:
                        display_logger.warning(
                            f"More than one document found for docsink {docsink.docsink_uuid}."
                        )
                        continue
                    document = documents[0]
                    if document.original_uri is None:
                        display_logger.warning(
                            f"Document {document.doc_uri} has no original uri."
                        )
                        continue
                    successful_documents[document.original_uri] = document
                except Exception as e:
                    pass

        else:
            for document in pipeline_utils.run_adhoc_pipeline_for_docsinks(
                exec_info=exec_info, docsink_create_list=docsink_create_list
            ):
                if document.original_uri is None:
                    display_logger.warning(
                        f"Document {document.doc_uri} has no original uri."
                    )
                    continue
                successful_documents[document.original_uri] = document
            docsource.docsource_status = DocSourceStatus.COMPLETED
            docsource_store.update_docsource(org, kb, docsource)

        display_logger.info(f"Scraped {len(successful_documents)} useful URLs.")

        return successful_documents
