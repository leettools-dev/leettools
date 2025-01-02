import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import factory_util
from leettools.context_manager import Context
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.settings import SystemSettings
from leettools.web.schemas.search_result import SearchResult


class AbstractRetriever(ABC):
    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        self.context = context
        self.org = org
        self.kb = kb
        self.user = user
        self.logger = logger()

    @abstractmethod
    def retrieve_search_result(
        self,
        search_keywords: str,
        flow_options: Optional[Dict[str, Any]] = {},
        display_logger: Optional[EventLogger] = None,
    ) -> List[SearchResult]:
        """
        Return the top results for the query from the retriever service for the given
        days limit.

        Args:
        - search_keywords: The keywords to search for
        - flow_options: The flow options to use for the search
        - display_logger: The logger to use for logging

        Returns:
        - List[SearchResult]: The search results
        """
        pass


def create_retriever(
    retriever_type: str,
    context: Context,
    org: Optional[Org],
    kb: Optional[KnowledgeBase],
    user: Optional[User],
) -> AbstractRetriever:
    """
    Create a retriever object based on the retriever type.

    Right now the only place outside of the web package that uses this function is the
    step_local_kb_search.py and flow_extractor in the flow package. They were used to
    search the local KB and get compatible search results. We should remove direct usage
    in those places and use the web_searcher.py instead.

    Args:
    - retriever_type: The type of retriever to create
    - context: The context object
    - org: The organization object
    - kb: The knowledge base object
    - user: The user object

    Returns:
    - The retriever object
    """

    if retriever_type is None or retriever_type == "":
        retriever_type = os.environ.get(SystemSettings.EDS_WEB_RETRIEVER)
        if retriever_type is None or retriever_type == "":
            retriever_type = RetrieverType.GOOGLE.value

    if type(retriever_type) is not str:
        retriever_type = retriever_type.value

    if "." not in retriever_type:
        module_name = f"{__package__}.{retriever_type}.{retriever_type}"
    else:
        module_name = retriever_type

    return factory_util.create_object(
        module_name,
        AbstractRetriever,
        context=context,
        org=org,
        kb=kb,
        user=user,
    )
