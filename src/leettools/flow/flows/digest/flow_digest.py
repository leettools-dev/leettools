from typing import ClassVar, Dict, List, Optional, Set, Type

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import flow_option_items, iterators, steps, subflows
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.utils import flow_utils
from leettools.web.web_searcher import WebSearcher


class FlowDigest(AbstractFlow):

    FLOW_TYPE: ClassVar[str] = FlowType.DIGEST.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.RESEARCH.value
    COMPONENT_NAME: ClassVar[str] = FlowType.DIGEST.value

    @classmethod
    def short_description(cls) -> str:
        return "Generate a multi-section digest article from search results."

    @classmethod
    def full_description(cls) -> str:
        return """
When interested in a topic, you can generate a digest article:
- Define search keywords and optional content instructions for relevance filtering.
- Perform the search with retriever: "local" for local KB, a search engine (e.g., Google)
  fetches top documents from the web. If no KB is specified, create an adhoc KB; 
  otherwise, save and process results in the KB.
- New web search results are processed through the document pipeline: conversion, 
  chunking, and indexing.
- Each result document is summarized using a LLM API call.
- Generate a topic plan for the digest from the document summaries.
- Create sections for each topic in the plan using content from the KB.
- Concatenate sections into a complete digest article.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [
            steps.StepGenSearchPhrases,
            steps.StepSearchToDocsource,
            steps.StepScrpaeUrlsToDocSource,
            steps.StepLocalKBSearch,
            subflows.SubflowGenEssay,
        ]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractFlow.get_flow_option_items() + [
            flow_option_items.FOI_RETRIEVER(explicit=True),
            flow_option_items.FOI_SEARCH_REWRITE(),
            flow_option_items.FOI_SEARCH_RECURSIVE_SCRAPE(),
            flow_option_items.FOI_SEARCH_RECURSIVE_SCRAPE_MAX_COUNT(),
            flow_option_items.FOI_SEARCH_RECURSIVE_SCRAPE_ITERATION(),
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: Optional[EventLogger] = None,
    ) -> ChatQueryResultCreate:

        # common setup
        exec_info = ExecInfo(
            context=self.context,
            org=org,
            kb=kb,
            user=user,
            target_chat_query_item=chat_query_item,
            display_logger=display_logger,
        )
        flow_options = exec_info.flow_options
        threshold = self.context.settings.RELEVANCE_THRESHOLD

        retriever_type = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_RETRIEVER_TYPE,
            default_value=exec_info.settings.WEB_RETRIEVER,
            display_logger=display_logger,
        )

        search_language = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_SEARCH_LANGUAGE,
            default_value=None,
            display_logger=display_logger,
        )

        search_rewrite = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_SEARCH_REWRITE,
            default_value=None,
            display_logger=display_logger,
        )

        # the agent flow starts here
        if search_language or search_rewrite:
            search_keywords = steps.StepGenSearchPhrases.run_step(exec_info=exec_info)
        else:
            search_keywords = chat_query_item.query_content

        if retriever_type == RetrieverType.LOCAL:
            search_results = steps.StepLocalKBSearch.run_step(
                exec_info=exec_info, query=search_keywords
            )
            document_summaries = ""
            for search_result in search_results:
                document_summaries += search_result.snippet
        else:
            recursive_scrape = config_utils.get_bool_option_value(
                options=flow_options,
                option_name=flow_option.FLOW_OPTION_RECURSIVE_SCRAPE,
                default_value=False,
                display_logger=display_logger,
            )

            recur_max_count = config_utils.get_int_option_value(
                options=flow_options,
                option_name=flow_option.FLOW_OPTION_RECURSIVE_SCRAPE_MAX_COUNT,
                default_value=10,
                display_logger=display_logger,
            )

            recur_iterations = config_utils.get_int_option_value(
                options=flow_options,
                option_name=flow_option.FLOW_OPTION_RECURSIVE_SCRAPE_ITERATION,
                default_value=3,
                display_logger=display_logger,
            )

            # accumulated states (including web_searcher, which will cache the visited urls)
            web_searcher = WebSearcher(context=self.context)
            # all the documents that have been summarized
            summarized_docs: Dict[str, Document] = {}
            # only keep the documents that are relevant
            final_docs: Dict[str, Document] = {}

            # links found in the search results, used when we do the recursive scrape
            all_links: Dict[str, int] = {}
            visted_links: Set[str] = set()
            iteration = 1

            # this is the initial search step
            docsource = steps.StepSearchToDocsource.run_step(
                exec_info=exec_info, search_keywords=search_keywords
            )

            document_store = exec_info.context.get_repo_manager().get_document_store()
            for doc in document_store.get_documents_for_docsource(org, kb, docsource):
                if doc.original_uri:
                    visted_links.add(doc.original_uri)

            summarized_docs = iterators.Summarize.run(
                exec_info=exec_info,
                docsource=docsource,
                all_links=all_links,
            )

            for url, doc in summarized_docs.items():
                visted_links.add(url)
                if doc:
                    if doc.summary().relevance_score >= threshold:
                        final_docs[url] = doc

            if recursive_scrape:
                while (
                    len(final_docs) < recur_max_count and iteration < recur_iterations
                ):
                    iteration += 1
                    target_links = []
                    # sort the links in the all_links dictionary by their scores
                    # remove any that have already been summarized
                    for url, score in sorted(
                        all_links.items(), key=lambda x: x[1], reverse=True
                    ):
                        display_logger.debug(f"[Digest]Checking url:[{score}] {url} ")
                        if url in visted_links:
                            continue

                        display_logger.debug(f"[Digest]Added to scrape targets: {url}")
                        target_links.append(url)
                        visted_links.add(url)

                        if len(target_links) >= recur_max_count - len(summarized_docs):
                            break

                    scraped_documents = steps.StepScrpaeUrlsToDocSource.run_step(
                        exec_info=exec_info,
                        web_searcher=web_searcher,
                        links=target_links,
                        docsource=docsource,
                    )

                    for url, document in scraped_documents.items():
                        newdoc = steps.StepSummarize.run_step(
                            exec_info=exec_info,
                            document=document,
                            all_links=all_links,
                        )
                        if not newdoc:
                            display_logger.debug(
                                f"[Digest]Processing returned None: {url}."
                            )
                            continue

                        summarized_docs[url] = newdoc
                        if newdoc.summary().relevance_score >= threshold:
                            final_docs[url] = newdoc
                        else:
                            display_logger.debug(
                                f"[Digest]Document is not relevant: "
                                f"[{newdoc.summary().relevance_score}] {url}"
                            )
                    display_logger.debug(
                        f"[Digest]Iteration {iteration}, "
                        f"final_docs: {len(final_docs)}, "
                        f"summarized_docs: {len(summarized_docs)}"
                    )

            document_summaries = ""
            for document in sorted(
                final_docs.values(),
                key=lambda x: x.summary().relevance_score,
                reverse=True,
            ):
                display_logger.debug(
                    f"[Digest] Adding document summary: {document.original_uri}, "
                    f"relevance: {document.summary().relevance_score}"
                )
                document_summaries += document.summary().summary + "\n"

        # now we have the document summaries from either local or web search
        if document_summaries == "" or document_summaries is None:
            display_logger.debug(f"[Digest] Document summaries is empty")
            return flow_utils.create_chat_result_for_empty_search(
                exec_info=exec_info, query_metadata=None
            )
        else:
            display_logger.debug(f"[Digest] Document summaries: {document_summaries}")

        return subflows.SubflowGenEssay.run_subflow(
            exec_info=exec_info,
            article_type=self.ARTICLE_TYPE,
            document_summaries=document_summaries,
        )
