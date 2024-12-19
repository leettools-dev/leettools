from abc import ABC, abstractmethod

from leettools.core.consts.return_code import ReturnCode
from leettools.core.repo.document_store import AbstractDocumentStore
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.settings import SystemSettings


class AbstractConverter(ABC):
    @abstractmethod
    def __init__(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsink: DocSink,
        settings: SystemSettings,
    ) -> None:
        """
        Initialize the converter.

        Args:
        docsink_list: The list of document sinks to convert.
        settings: The system settings.
        """
        pass

    @abstractmethod
    def convert(self) -> ReturnCode:
        """
        Convert a list of document sinks to a list of documents
        and save them to the docstore.

        Args:
        doc_sink: The docsink to convert.

        Returns:
        The document created from the document sink.
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


def create_converter(
    org: Org,
    kb: KnowledgeBase,
    docsink: DocSink,
    docstore: AbstractDocumentStore,
    settings: SystemSettings,
) -> AbstractConverter:
    """
    Factory function to create an converter based on the document source.

    Args:
    settings: The system settings.

    Returns:
    An converter for the document source.
    """
    from ._impl.converter_local import ConverterLocal

    return ConverterLocal(org, kb, docsink, docstore, settings)
