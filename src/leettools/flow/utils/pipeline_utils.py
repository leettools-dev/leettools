from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import List

from leettools.common.logging import logger
from leettools.common.logging.log_location import LogLocator
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.consts.document_status import DocumentStatus
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.docsink import DocSink, DocSinkCreate
from leettools.core.schemas.document import Document
from leettools.core.schemas.segment import Segment
from leettools.eds.pipeline.convert.converter import create_converter
from leettools.eds.pipeline.embed.segment_embedder import create_segment_embedder_for_kb
from leettools.eds.pipeline.split.splitter import Splitter
from leettools.flow.exec_info import ExecInfo


def run_adhoc_pipeline_for_docsinks(
    exec_info: ExecInfo,
    docsink_create_list: List[DocSinkCreate],
) -> List[Document]:
    """
    Given the list of docsink_creates, run the doc pipeline and return the list of
    documents that have been processed successfully.

    Args:
    - exec_info: Execution information
    - docsink_create_list: The list of docsink_creates to process

    Returns:
    - List[Document]: The list of documents that have been processed successfully
    """

    context = exec_info.context
    display_logger = exec_info.display_logger
    org = exec_info.org
    kb = exec_info.kb
    user = exec_info.user
    query = exec_info.query

    docsink_store = context.get_repo_manager().get_docsink_store()
    docstore = context.get_repo_manager().get_document_store()
    segment_store = context.get_repo_manager().get_segment_store()

    log_dir = LogLocator.get_log_dir_for_query(
        chat_id=exec_info.target_chat_query_item.chat_id,
        query_id=exec_info.target_chat_query_item.query_id,
    )
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_location = f"{log_dir}/web_search_job.log"
    display_logger.info(f"Web search job log location: {log_location}")
    with open(log_location, "a+") as f:
        f.write(f"Job log for web search {query} created at {datetime.now()}\n")

    display_logger.info("Adhoc query: converting documents to markdown ...")

    def _convert_helper(docsink_create: DocSinkCreate) -> DocSink:
        # this function may create a new docsink or return an existing one
        docsink = docsink_store.create_docsink(org, kb, docsink_create)
        if docsink is None:
            display_logger.error(
                f"Adhoc query: failed to create docsink for {docsink_create}"
            )
            return None
        display_logger.debug(
            f"The docsink created has status: {docsink.docsink_status}"
        )
        docsource_uuid = docsink_create.docsource_uuid
        if docsource_uuid != docsink.docsource_uuid:
            display_logger.info(
                f"Adhoc query: docsink {docsink.docsink_uuid} already created before."
            )
            return docsink
        converter = create_converter(
            org=org,
            kb=kb,
            docsink=docsink,
            docstore=docstore,
            settings=context.settings,
        )
        converter.set_log_location(log_location)
        rtn_code = converter.convert()
        if rtn_code == ReturnCode.SUCCESS:
            display_logger.debug("Adhoc query: converted document to markdown")
            docsink.docsink_status = DocSinkStatus.PROCESSING
        else:
            display_logger.error(
                f"Adhoc query: failed to convert document to markdown {rtn_code}"
            )
            docsink.docsink_status = DocSinkStatus.FAILED
        docsink_store.update_docsink(org, kb, docsink)
        return docsink

    docsinks: List[DocSink] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for docsink in executor.map(_convert_helper, docsink_create_list):
            if docsink:
                docsinks.append(docsink)

    display_logger.info("✅ Adhoc query: finished converting documents to markdown.")
    display_logger.info("Adhoc query: start to chunk documents ...")

    documents: List[Document] = []
    for docsink in docsinks:
        doc_for_docsink = docstore.get_documents_for_docsink(org, kb, docsink)
        if not doc_for_docsink:
            display_logger.warning(
                f"Adhoc query: no documents found for docsink {docsink.docsink_uuid}, which should not happen."
            )
            continue
        if len(doc_for_docsink) > 1:
            display_logger.debug(
                f"Adhoc query: multiple documents found for docsink {docsink.docsink_uuid}, which should not happen."
            )
            for doc in doc_for_docsink:
                display_logger.debug(
                    f"Adhoc query duplicate docs docsink {docsink.docsink_uuid}: document {doc.document_uuid} {doc.original_uri}"
                )
        documents.append(doc_for_docsink[0])

    splitter = Splitter(context=context, org=org, kb=kb)

    def _split_helper(log_file_location: str, doc: Document) -> Document:
        rnt_code = splitter.split(doc=doc, log_file_location=log_file_location)
        if rnt_code == ReturnCode.SUCCESS:
            display_logger.debug(
                "Adhoc query: split documents to segments successfully"
            )
            doc.split_status = DocumentStatus.COMPLETED
        else:
            display_logger.error(
                f"Adhoc query: failed to split documents to segments, return code: {rnt_code}."
            )
            doc.split_status = DocumentStatus.FAILED
        docstore.update_document(org, kb, doc)
        return doc

    partial_splitter = partial(_split_helper, log_location)
    success_documents: List[Document] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for doc in executor.map(partial_splitter, documents):
            if doc.split_status == DocumentStatus.COMPLETED:
                success_documents.append(doc)

    display_logger.info("✅ Adhoc query: finished chunking documents.")
    display_logger.info("Adhoc query: start to embed document chunks ...")

    embedder = create_segment_embedder_for_kb(
        org=org, kb=kb, user=user, context=context
    )

    segments: List[Segment] = []

    for doc in success_documents:
        segments_for_doc = segment_store.get_all_segments_for_document(
            org, kb, doc.document_uuid
        )
        segments.extend(segments_for_doc)

    display_logger.info(f"Adhoc query: got all the chunks {len(segments)} ...")
    job_logger = logger()
    log_handler = None
    if log_location:
        log_handler = job_logger.log_to_file(log_location)
    try:
        embedder.embed_segment_list(segments=segments, display_logger=job_logger)
        display_logger.info("Adhoc query: embedded all the chunks ...")
    finally:
        if log_handler:
            job_logger.remove_file_handler()

    # for adhoc query, we update status to completed for ALL documents and docsinks
    for doc in documents:
        doc.embed_status = DocumentStatus.COMPLETED
        docstore.update_document(org, kb, doc)

    for docsink in docsinks:
        docsink.docsink_status = DocSinkStatus.COMPLETED
        docsink_store.update_docsink(org, kb, docsink)

    display_logger.info("✅ Adhoc query: finished embedding documents chunks.")

    return success_documents
