from typing import Callable, Generator, Optional

from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.flow.exec_info import ExecInfo


def document_iterator(
    exec_info: ExecInfo,
    docsource: Optional[DocSource] = None,
    docsource_filter: Optional[Callable[[ExecInfo, DocSource], bool]] = None,
    docsink_filter: Optional[Callable[[ExecInfo, DocSink], bool]] = None,
    document_filter: Optional[Callable[[ExecInfo, Document], bool]] = None,
) -> Generator[Document, None, None]:
    """
    Iterate over all documents for the KB in exec_info or a specified docsource.

    It is possible to just use the docsource_filter to filter out the target docsource.
    We allow to specify the docsource directly to avoid the need to get all docsources
    from the KB and then filter them.

    Args:
    - exec_info: Execution information.
    - docsource: Optional docsource to iterate over.
    - docsource_filter: Optional filter for docsources, n/a if docsource is specified.
    - docsink_filter: Optional filter for docsinks.
    - document_filter: Optional filter for documents.

    Returns:
    - Generator of documents.
    """

    context = exec_info.context
    docsink_store = context.get_repo_manager().get_docsink_store()
    document_store = context.get_repo_manager().get_document_store()
    org = exec_info.org
    kb = exec_info.kb
    display_logger = exec_info.display_logger

    def _get_doc_for_docsink(docsource: DocSource) -> Generator[Document, None, None]:
        for docsink in docsink_store.get_docsinks_for_docsource(org, kb, docsource):
            if docsink_filter is not None:
                if not docsink_filter(exec_info, docsink):
                    continue

            for document in document_store.get_documents_for_docsink(org, kb, docsink):
                if document_filter is not None:
                    if not document_filter(exec_info, document):
                        continue

                yield document

    if docsource is not None:
        if docsource_filter is not None:
            display_logger.warning(
                "Specified both docsource and docsource_filter, ignoring filter."
            )
        yield from _get_doc_for_docsink(docsource)
        return

    docsource_store = context.get_repo_manager().get_docsource_store()
    for docsource in docsource_store.get_docsources_for_kb(org, kb):
        if docsource_filter is not None:
            if not docsource_filter(exec_info, docsource):
                continue
        yield from _get_doc_for_docsink(docsource)
