from typing import ClassVar, List, Optional, Type

from leettools.core.consts.retriever_type import RetrieverType
from leettools.flow import flow_option_items
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.step import AbstractStep
from leettools.web.retrievers.retriever import create_retriever
from leettools.web.schemas.search_result import SearchResult


class StepLocalKBSearch(AbstractStep):

    COMPONENT_NAME: ClassVar[str] = "local_kb_search"

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        # right now here we still need to get the flow options items
        # manually from all the functions used in this step
        return AbstractStep.get_flow_option_items() + [
            flow_option_items.FOI_DAYS_LIMIT(),
            flow_option_items.FOI_SEARCH_MAX_RESULTS(),
        ]

    @staticmethod
    def run_step(
        exec_info: ExecInfo, query: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search the local KB with the query and get the top documents for the query.

        Args:
        - exec_info: Execution information
        - query: The query to search

        Returns:
        - the list of search results
        """
        if query is None:
            query = exec_info.query

        retriever = create_retriever(
            retriever_type=RetrieverType.LOCAL,
            context=exec_info.context,
            org=exec_info.org,
            kb=exec_info.kb,
            user=exec_info.user,
        )
        search_results = retriever.retrieve_search_result(
            search_keywords=query,
            flow_options=exec_info.flow_options,
            display_logger=exec_info.display_logger,
        )
        return search_results
