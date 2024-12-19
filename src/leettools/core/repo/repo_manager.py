from leettools.core.repo.docgraph_store import (
    AbstractDocGraphStore,
    create_docgraph_store,
)
from leettools.core.repo.docsink_store import AbstractDocsinkStore, create_docsink_store
from leettools.core.repo.docsource_store import (
    AbstractDocsourceStore,
    create_docsource_store,
)
from leettools.core.repo.document_store import (
    AbstractDocumentStore,
    create_document_store,
)
from leettools.core.repo.segment_store import AbstractSegmentStore, create_segment_store
from leettools.settings import SystemSettings


class RepoManager:
    """
    The RepoManager is a class that manages the repositories for all KBs, the
    documentstore, segmentstore, and graphstore. It provides access to the repositories
    and is responsible for creating and initializing them.
    """

    def __init__(self, settings: SystemSettings) -> None:
        self.settings = settings
        self._ducument_store = create_document_store(settings)
        self._segment_store = create_segment_store(settings)
        self._docgraph_store = create_docgraph_store(settings)
        self._docsource_store = create_docsource_store(settings)
        self._docsink_store = create_docsink_store(settings)

    def get_document_store(self) -> AbstractDocumentStore:
        return self._ducument_store

    def get_segment_store(self) -> AbstractSegmentStore:
        return self._segment_store

    def get_docgraph_store(self) -> AbstractDocGraphStore:
        return self._docgraph_store

    def get_docsource_store(self) -> AbstractDocsourceStore:
        return self._docsource_store

    def get_docsink_store(self) -> AbstractDocsinkStore:
        return self._docsink_store
