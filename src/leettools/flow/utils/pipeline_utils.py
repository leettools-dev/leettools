from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import List

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.common.logging.log_location import LogLocator
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.consts.document_status import DocumentStatus
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.chat_query_item import (
    DUMMY_QUERY_CONTENT,
    DUMMY_QUERY_ID,
    ChatQueryItem,
)
from leettools.core.schemas.docsink import DocSink, DocSinkCreate
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.core.schemas.user import User
from leettools.eds.pipeline.convert.converter import create_converter
from leettools.eds.pipeline.embed.segment_embedder import create_segment_embedder_for_kb
from leettools.eds.pipeline.ingest.connector import create_connector
from leettools.eds.pipeline.split.splitter import Splitter
from leettools.eds.scheduler.scheduler_manager import run_scheduler
from leettools.flow.exec_info import ExecInfo


def process_docsources_auto(
    org: Org,
    kb: KnowledgeBase,
    docsources: List[DocSource],
    context: Context,
    display_logger: EventLogger,
) -> List[DocSource]:
    """
    Process the docsource that is auto-scheduled. This function will check if the scheduler
    is running, if not, it will start the scheduler to process the docsource. If the scheduler
    is running, it will wait for the docsource to be processed.

    Args:
    - org: The organization
    - kb: The knowledge base
    - docsources: The list of docsources to process
    - context: The context
    - display_logger: The display logger

    Returns:
    - The updated docsources
    """
    if kb.auto_schedule == False:
        raise exceptions.UnexpectedCaseException(
            f"The KB {kb.name} is not set to auto-schedule."
        )

    docsource_store = context.get_repo_manager().get_docsource_store()

    if context.scheduler_is_running:
        display_logger.info("Scheduled the new DocSource to be processed ...")
        started = False
    else:
        display_logger.info("Start the scheduler to process the new DocSources ...")
        started = run_scheduler(context=context, org=org, kb=kb, docsources=docsources)

    # TODO next: the scheduler should provide an async function to check the status
    # TODO next: the timeout is hard-coded here
    if started == False:
        # another process is running the scheduler
        for docsource in docsources:
            finished = docsource_store.wait_for_docsource(
                org, kb, docsource, timeout_in_secs=300
            )
            if finished == False:
                display_logger.warning(
                    f"The docsource has not finished processing yet: {docsource.uri}."
                )
    else:
        # the scheduler has been started and finished processing
        pass
    updated_docsources: List[DocSource] = []
    for docsource in docsources:
        updated_docsources.append(
            docsource_store.get_docsource(org, kb, docsource.docsource_uuid)
        )
    return updated_docsources


def process_docsource_manual(
    org: Org,
    kb: KnowledgeBase,
    user: User,
    docsource: DocSource,
    context: Context,
    display_logger: EventLogger,
) -> DocSource:
    docsink_store = context.get_repo_manager().get_docsink_store()
    docsource_store = context.get_repo_manager().get_docsource_store()
    connector = create_connector(
        context=context,
        connector="connector_simple",
        org=org,
        kb=kb,
        docsource=docsource,
        docsinkstore=docsink_store,
        display_logger=display_logger,
    )
    connector.ingest()
    docsink_create_list = connector.get_ingested_docsink_list()
    exec_info: ExecInfo = ExecInfo(
        context=context,
        org=org,
        kb=kb,
        user=user,
        display_logger=logger(),
        target_chat_query_item=ChatQueryItem(
            query_content=DUMMY_QUERY_CONTENT,
            query_id=DUMMY_QUERY_ID,
            created_at=time_utils.current_datetime(),
        ),
    )
    run_adhoc_pipeline_for_docsinks(
        exec_info=exec_info, docsink_create_list=docsink_create_list
    )
    return docsource_store.get_docsource(org, kb, docsource.docsource_uuid)


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

    docsink_store = context.get_repo_manager().get_docsink_store()
    docstore = context.get_repo_manager().get_document_store()
    segment_store = context.get_repo_manager().get_segment_store()

    if exec_info.target_chat_query_item is not None:
        query = exec_info.query
        log_dir = LogLocator.get_log_dir_for_query(
            chat_id=exec_info.target_chat_query_item.chat_id,
            query_id=exec_info.target_chat_query_item.query_id,
        )
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        log_location = f"{log_dir}/web_search_job.log"
        display_logger.info(f"Web search job log location: {log_location}")
        with open(log_location, "a+", encoding="utf-8") as f:
            f.write(
                f"Job log for web search {query} created at {time_utils.current_datetime()}\n"
            )

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
        if len(docsink.docsource_uuids) > 1:
            display_logger.debug(
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
        if doc.split_status == DocumentStatus.COMPLETED:
            display_logger.debug(
                f"Adhoc query: document {doc.document_uuid} already split."
            )
            return doc
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
        if doc.embed_status == DocumentStatus.COMPLETED:
            display_logger.debug(
                f"Adhoc query: document {doc.document_uuid} already embedded."
            )
            continue
        segments_for_doc = segment_store.get_all_segments_for_document(
            org, kb, doc.document_uuid
        )
        segments.extend(segments_for_doc)

    display_logger.info(
        f"Adhoc query: number of chunks to embed is {len(segments)} ..."
    )
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

    display_logger.info("✅ Adhoc query: finished processing docsinks.")

    return success_documents
