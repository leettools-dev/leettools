from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List

from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.document_status import DocumentStatus
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.docsink import DocSinkCreate
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import Segment
from leettools.eds.pipeline.convert.converter import create_converter
from leettools.eds.pipeline.embed.segment_embedder import \
    create_segment_embedder_for_kb
from leettools.eds.pipeline.ingest.connector import create_connector
from leettools.eds.pipeline.split.splitter import Splitter
from leettools.flow.exec_info import ExecInfo


def standalone_converter(raw_doc_path: str, 
                        context: Context,
                        org: Org,
                        kb: KnowledgeBase):
    """
    Run a standalone document converter pipeline.
    
    Args:
        raw_doc_path (Path): Path to the folder including raw documents to be converted
        context (Context): Application context
        org (Org): Organization instance
        kb (KnowledgeBase): Knowledge base instance
    
    Returns:
        ReturnCode: Status of the conversion process
    """
    # Get repository managers
    display_logger = logger()
    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()
    docsink_store = repo_manager.get_docsink_store()
    docstore = repo_manager.get_document_store()

    # Check if docsource already exists for this path
    existing_docsources = docsource_store.get_docsources_for_kb(org=org, kb=kb)
    docsource = None
    # Look for an existing docsource with the same URI
    for existing_docsource in existing_docsources:
        if existing_docsource.uri == str(raw_doc_path):
            docsource = existing_docsource
            display_logger.info(f"Found existing docsource {docsource.docsource_uuid} for path {raw_doc_path}")
            break
    # Create new docsource if not found
    if docsource is None:
        docsource_create = DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.LOCAL,
            uri=str(raw_doc_path),
        )
        docsource = docsource_store.create_docsource(org=org, kb=kb, docsource_create=docsource_create)
        display_logger.info(f"Created new docsource {docsource.docsource_uuid} for path {raw_doc_path}")

    # Create a connector to handle the ingestion
    connector = create_connector(
        context=context,
        connector="connector_simple",
        org=org,
        kb=kb,
        docsource=docsource,
        docsinkstore=docsink_store
    )
    
    # Use the connector to ingest files and get docsink list
    connector.ingest()
    docsink_create_list = connector.get_ingested_docsink_list()
    
    # Convert documents helper function
    def _convert_helper(docsink_create):
        # Create docsink from the docsink_create
        docsink = docsink_store.create_docsink(org, kb, docsink_create)
        if docsink is None:
            display_logger.error(
                f"Failed to create docsink for {docsink_create}"
            )
            return None
            
        # TODO: Following doesn't work to check whether the docsink is already processed, fail to skip    
        if len(docsink.docsource_uuids) > 1:
            display_logger.debug(
                f"Docsink {docsink.docsink_uuid} already created before."
            )
            return docsink
            
        # Check if markdown file already exists
        # document = docstore.get_document_by_id(org, kb, docsink.docsink_uuid)
        document = docstore.get_documents_for_docsink(org, kb, docsink)
        if document: # TODO: Not a safe check, may need to be improved in the future
            display_logger.debug(
                f"Document {docsink.docsink_uuid} already has markdown content, skipping conversion."
            )
            return docsink
            
        # Create converter and run conversion
        converter = create_converter(
            org=org,
            kb=kb,
            docsink=docsink,
            docstore=docstore,
            settings=context.settings,
        )
 
        rtn_code = converter.convert()
        if rtn_code == ReturnCode.SUCCESS:
            display_logger.debug(f"Successfully converted document {docsink.docsink_uuid}")
            docsink.docsink_status = DocSinkStatus.PROCESSING
        else:
            display_logger.error(
                f"Failed to convert document {docsink.docsink_uuid}: {rtn_code}"
            )
            docsink.docsink_status = DocSinkStatus.FAILED
            
        docsink_store.update_docsink(org, kb, docsink)
        return docsink
    
    # Process docsinks in parallel with ThreadPoolExecutor
    docsinks = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for docsink in executor.map(_convert_helper, docsink_create_list):
            if docsink:
                docsinks.append(docsink)
                
    display_logger.info(f"Converted {len(docsinks)} documents into markdown successfully")


# TODO: enable this pipeline to use hardlinked parsed documents from other KBs
def standalone_splitter_embedder(org: Org, 
                                 kb: KnowledgeBase,
                                 exec_info: ExecInfo,
                                 user):
    """
    Run a standalone document splitter and embedder pipeline.
    
    Args:
        org (Org): Organization instance
        kb (KnowledgeBase): Knowledge base instance
        exec_info (ExecInfo): Execution information
    
    Returns:
        ReturnCode: Status of the splitter and embedder process
    """
    context, display_logger  = exec_info.context, exec_info.display_logger
    repo_manager = context.get_repo_manager()
    docstore = repo_manager.get_document_store()
    docsink_store = repo_manager.get_docsink_store()
    docsinks = docsink_store.get_docsinks_for_kb(org, kb)
    

    '''
    ===========================================================================
     Chunk/Split documents
    ===========================================================================
    '''
    display_logger.info("Adhoc query: start to chunk documents ...")
    documents = [docstore.get_documents_for_docsink(org, kb, docsink)[0] for docsink in docsinks]
    splitter = Splitter(context=context, org=org, kb=kb)
    def _split_helper(doc: Document) -> Document:
        if doc.split_status == DocumentStatus.COMPLETED:
            display_logger.debug(
                f"Adhoc query: document {doc.document_uuid} already split."
            )
            return doc
        rnt_code = splitter.split(doc=doc)
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
    
    partial_splitter = partial(_split_helper)
    success_documents: List[Document] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for doc in executor.map(partial_splitter, documents):
            if doc.split_status == DocumentStatus.COMPLETED:
                success_documents.append(doc)
    display_logger.info("✅ Adhoc query: finished chunking documents.")


    '''
    ===========================================================================
     Embed document chunks
    ===========================================================================
    '''
    display_logger.info("Adhoc query: start to embed document chunks ...")
    embedder = create_segment_embedder_for_kb( # NOTE: why it requires user???
        org=org, kb=kb, context=context, user=user
    )

    segments: List[Segment] = []
    segment_store = context.get_repo_manager().get_segment_store()
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
    


