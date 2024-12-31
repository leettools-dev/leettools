from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.consts.return_code import ReturnCode
from leettools.core.repo.docsink_store import AbstractDocsinkStore
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org


class AbstractConnector(ABC):

    @abstractmethod
    def __init__(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        docsinkstore: AbstractDocsinkStore,
        display_logger: Optional[EventLogger] = None,
    ) -> None:
        pass

    @abstractmethod
    def ingest(self) -> ReturnCode:
        """
        Ingest a document source into the system.
        Update the status of the document source accordingly.

        Args:
        doc_source: The document source to ingest.

        Returns:
        A list of the docsinks created from the document source.
        """
        pass

    @abstractmethod
    def set_log_location(self, log_location: str) -> None:
        """
        Set the location of the log file.

        Args:
        log_location: The location of the log file.
        """
        pass

    @abstractmethod
    def get_ingested_docsink_list(self) -> Optional[List[DocSinkCreate]]:
        """
        Get the list of docsinks created from the document source.

        Returns:
        A list of the docsinks created from the document source.
        """
        pass


# TODO: remove docsinkstore from the API?
def create_connector(
    context: Context,
    connector: str,
    org: Org,
    kb: KnowledgeBase,
    docsource: DocSource,
    docsinkstore: AbstractDocsinkStore,
    display_logger: Optional[EventLogger] = None,
) -> AbstractConnector:
    # Construct the target module name using the current package
    from leettools.common.utils import factory_util

    if "." not in connector:
        module_name = f"{__package__}._impl.{connector}"
    else:
        module_name = connector

    return factory_util.create_object(
        module_name,
        AbstractConnector,
        context=context,
        org=org,
        kb=kb,
        docsource=docsource,
        docsinkstore=docsinkstore,
        display_logger=display_logger,
    )
