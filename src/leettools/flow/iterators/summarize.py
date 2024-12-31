import traceback
from typing import Dict, List, Optional, Type

from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.flow import steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.iterator import AbstractIterator
from leettools.flow.iterators.document_iterator import document_iterator
from leettools.flow.steps.step_summarize import StepSummarize


class Summarize(AbstractIterator):

    from typing import ClassVar

    from leettools.flow.flow_component import FlowComponent
    from leettools.flow.flow_option_items import FlowOptionItem

    COMPONENT_NAME: ClassVar[str] = "Summarize"

    @classmethod
    def short_description(cls) -> str:
        return "Summarize the metadata and save them to the database."

    @classmethod
    def full_description(cls) -> str:
        return """
For each document specified by the iterator, summarize the metadata such as keywords,
links, content, authors, etc. and save them to the database.
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [steps.StepSummarize]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        return AbstractIterator.direct_flow_option_items() + []

    @staticmethod
    def run(
        exec_info: ExecInfo,
        docsource: Optional[DocSource] = None,
        all_links: Dict[str, int] = {},
        force_summarize: Optional[bool] = False,
    ) -> Dict[str, Document]:
        """
        Summarize the documents in the KB in the exec_info or the docsource if specified.

        Args:
        - exec_info: The execution information.
        - docsource: The docsource to summarize if specified.
        - all_links: Accumulated links with their counts.
        - force_summarize: Whether to force summarize the documents.

        Returns:
        - the dictionary of documents that are successfully summarized. The key is the
             url.
        """
        display_logger = exec_info.display_logger
        display_logger.info("[Status]Summarizing documents for metadata ...")

        successful_documents: Dict[str, Document] = {}

        for document in document_iterator(
            exec_info=exec_info,
            docsource=docsource,
        ):
            try:
                update_document = StepSummarize.run_step(
                    exec_info=exec_info,
                    document=document,
                    all_links=all_links,
                    force_summarize=force_summarize,
                )
                # the return value is None if the document has not been processed
                if update_document is not None:
                    successful_documents[document.original_uri] = update_document
            except Exception as e:
                display_logger.warning(
                    f"Ignore document failed to summarize {document.document_uuid}: {e}."
                )
                trace = traceback.format_exc()
                display_logger.warning(f"Detailed error: {trace}")
                continue

        display_logger.info(
            f"Finished summarzing, current link count: {len(all_links)}."
        )
        return successful_documents
