import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote

from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.common.utils.tokenizer import Tokenizer
from leettools.context_manager import Context
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SegmentCreate, SegmentInDB
from leettools.core.schemas.user import User
from leettools.eds.api_caller import api_utils
from leettools.eds.pipeline.chunk.chunker import create_chunker
from leettools.settings import is_media_file, supported_file_extensions

SEGMENTS = "segments"
GRAPH_ID_ATTR = "graph_id"

HEADING_PATTERN = re.compile(r"^(#+)\s*(.*)")
TITLE_PATTERN = re.compile(r"^Title:\s*(.*)", re.IGNORECASE)

ROOT_POSITION = "0"


def add_heading_to_content(heading: str, content: str) -> str:
    return f"{heading}@@{content}"


def remove_heading_from_content(content: str) -> str:
    # Find the last occurrence of "@@"
    last_at_index = content.rfind("@@")

    # If "@@" is found, slice from the index after "@@" onward
    if last_at_index != -1:
        return content[last_at_index + 2 :]  # Add 2 to move past the "@@"
    else:
        return content  # Return the original text if "@@" is not found


def separate_heading_from_content(content: str) -> Tuple[str, str]:
    # Find the last occurrence of "@@"
    last_at_index = content.rfind("@@")

    # If "@@" is found, slice from the index after "@@" onward
    if last_at_index != -1:
        return (
            content[:last_at_index],
            content[last_at_index + 2 :],
        )  # Add 2 to move past the "@@"
    else:
        return "", content  # Return the original text if "@@" is not found


CONTEXTUAL_RETRIEVAL_SYSTEM_PROMPT = """
You are a helpful assistant that can help to add the context to the chunk content.
"""

CONTEXTUAL_RETRIEVAL_USER_PROMPT = """
<document> 
{document_content} 
</document> 
Here is the chunk we want to situate within the whole document 
<chunk> 
{chunk_content} 
</chunk> 
Please give a short succinct context to situate this chunk within the overall document 
for the purposes of improving search retrieval of the chunk. Answer only with the 
succinct context and nothing else. 
The response should be in the following json format (Make sure the "document", "paragraph_id", "summary" 
and "other_info" are in the same language as the chunk itself):
{{
    "document": "the document name",
    "paragraph_id": "the id of the paragraph in the document, i.e. 1.1, 1.2, 2.1, etc.",
    "summary": "a short summary of the paragraph",
    "other_info": "other information about the paragraph, such as the title, author, etc."
}}
"""

# we can put the above prompts into a text file and load them in a strategy section
_script_dir = os.path.dirname(os.path.abspath(__file__))


class Splitter:
    """
    The Splitter class is our wrapper class to run the following process:
    1. Split the document into chunks using the chunker
    2. Add the context to the chunk content
    3. Optional: create retrieval context for the chunk
    4. Save the chunk texts to the document store
    5. Embed the chunks to the vector store
    6. Update the graph store with the parent-child relationships
    7. Optional [TOOD]: update the entity graph in the graph store
    """

    def __init__(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
    ) -> None:
        self.org = org
        self.kb = kb
        self.context = context
        repo_manager = context.get_repo_manager()
        self.docstore = repo_manager.get_document_store()
        self.segstore = repo_manager.get_segment_store()
        self.graphstore = repo_manager.get_docgraph_store()
        self.user_store = context.get_user_store()

        if kb.user_uuid is not None:
            self.user = self.user_store.get_user_by_uuid(kb.user_uuid)
        else:
            self.user = User.get_admin_user()
        self.settings = context.settings
        self.tokenizer = Tokenizer(self.settings)

    def _add_context_summary_to_chunk(
        self,
        chunk_content: str,
        document_for_contextual_retrieval: str,
    ) -> str:
        """
        Add the context summary to the chunk content when contextual retrieval is enabled.

        Args:
        - chunk_content: the content of the chunk
        - document_for_contextual_retrieval: the document content for contextual retrieval
        """
        user_prompt = CONTEXTUAL_RETRIEVAL_USER_PROMPT.format(
            document_content=document_for_contextual_retrieval,
            chunk_content=chunk_content,
        )

        api_provider_config = api_utils.get_default_inference_api_provider_config(
            context=self.context, user=self.user
        )
        api_client = api_utils.get_openai_client_for_user(
            context=self.context,
            user=self.user,
            api_provider_config=api_provider_config,
        )
        model_options = {}
        model_name = api_utils.get_default_inference_model_for_user(
            context=self.context, user=self.user
        )
        try:
            (context_summary, _) = api_utils.run_inference_call_direct(
                context=self.context,
                user=self.user,
                api_client=api_client,
                api_provider_name=api_provider_config.api_provider,
                model_name=model_name,
                model_options=model_options,
                system_prompt=CONTEXTUAL_RETRIEVAL_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                need_json=True,
                call_target="CONTEXTUAL RETRIEVAL",
                response_pydantic_model=None,
                display_logger=logger(),
            )
        except Exception as e:
            logger().error(f"Error adding context to chunk: {e}")
            return chunk_content
        return f"\n<context>\n{context_summary}\n</context>\n{chunk_content}"

    def _find_parent_child_pairs(
        self, pos_map: Dict[str, int]
    ) -> List[Tuple[int, int]]:
        pairs = []
        for child_position in pos_map.keys():
            if "." not in child_position and child_position != ROOT_POSITION:
                parent_position = ROOT_POSITION
                pairs.append((pos_map[parent_position], pos_map[child_position]))
            else:
                if "." in child_position:
                    parent_position = child_position.rsplit(".", 1)[0]
                    while parent_position not in pos_map and "." in parent_position:
                        parent_position = parent_position.rsplit(".", 1)[0]
                    if parent_position in pos_map:
                        pairs.append(
                            [pos_map[parent_position], pos_map[child_position]]
                        )
        return pairs

    def _save2segmentstore(
        self,
        segment_create: SegmentCreate,
    ) -> SegmentInDB:
        return self.segstore.create_segment(self.org, self.kb, segment_create)

    def _save2graphdb(self, segment_in_db: SegmentInDB) -> None:
        graph_node_id = self.graphstore.create_segment_node(segment_in_db)
        segment_in_db.graph_node_id = graph_node_id

    def _update_doc_graph(self, doc_postion_map: Dict[str, int]) -> None:
        parent_child_pairs = self._find_parent_child_pairs(doc_postion_map)
        for parent_id, child_id in parent_child_pairs:
            self.graphstore.create_segments_relationship(parent_id, child_id)

    def _split(self, doc: Document) -> ReturnCode:
        rtn_code = ReturnCode.SUCCESS

        doc_uri = doc.doc_uri
        file_path = Path(doc_uri)
        if is_media_file(file_path.suffix):
            return rtn_code

        # since doc_uri may contain some useful information,
        # we need to add doc_uri at the beginning of the content
        base_name = doc_uri.split("/")[-1]
        base_name = ".".join(base_name.split(".")[:-1])
        doc_uri_unqoted = unquote(base_name).replace("_", " ").replace("-", " ")
        for ext in supported_file_extensions():
            doc_uri_unqoted = doc_uri_unqoted.replace(ext, "")

        logger().debug(f"Splitting document: {doc_uri} to KB {self.kb.name}")
        chunker = create_chunker(settings=self.settings)
        chunks = chunker.chunk(doc.content)

        doc_postion_map: Dict[str, int] = {}
        epoch_time_ms = time_utils.cur_timestamp_in_ms()

        """
        Get the document content for contextual retrieval.
        Note: we can't directly use the document content from document store,
        because it may contain more tokens than the contextlimit of the LLM model.
        """
        if self.kb.enable_contextual_retrieval:
            if (
                self.tokenizer.token_count(doc.content)
                < self.settings.DEFAULT_CONTEXT_LIMIT
            ):
                logger().info(
                    "Using the whole document content for contextual retrieval"
                )
                document_for_contextual_retrieval = doc.content
            else:
                chunk_list_for_contextual_retrieval = []
                context_token_count = 0
                logger().info("Combining chunks for contextual retrieval")
                for chunk in chunks:
                    chunk_token_count = self.tokenizer.token_count(chunk.content)
                    if (
                        context_token_count + chunk_token_count
                        < self.settings.DEFAULT_CONTEXT_LIMIT
                    ):
                        chunk_list_for_contextual_retrieval.append(chunk)
                        context_token_count += chunk_token_count
                    else:
                        # we don't want to include too many chunks for context retrieval
                        break
                document_for_contextual_retrieval = "\n".join(
                    [chunk.content for chunk in chunk_list_for_contextual_retrieval]
                )
        # end of getting the document content for contextual retrieval

        for chunk in chunks:
            if self.kb.enable_contextual_retrieval:
                chunk_content = self._add_context_summary_to_chunk(
                    chunk.content, document_for_contextual_retrieval
                )
            else:
                chunk_content = chunk.content

            segmeng_create = SegmentCreate(
                content=add_heading_to_content(
                    heading=f"{doc_uri_unqoted}@@{chunk.heading}", content=chunk_content
                ),
                document_uuid=doc.document_uuid,
                doc_uri=doc_uri,
                docsink_uuid=doc.docsink_uuid,
                kb_id=self.kb.name,
                original_uri=doc.original_uri,
                position_in_doc=chunk.position_in_doc,
                heading=chunk.heading,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                created_timestamp_in_ms=epoch_time_ms,
                label_tag=str(epoch_time_ms),
            )
            segment_in_db = self._save2segmentstore(segmeng_create)
            self._save2graphdb(segment_in_db)
            doc_postion_map[chunk.position_in_doc] = segment_in_db.graph_node_id

        root_segment = SegmentCreate(
            content="The root segment",
            document_uuid=doc.document_uuid,
            doc_uri=doc_uri,
            docsink_uuid=doc.docsink_uuid,
            kb_id=self.kb.name,
            original_uri=doc.original_uri,
            position_in_doc=ROOT_POSITION,
            heading="Root",
            start_offset=0,
            end_offset=0,
            created_timestamp_in_ms=epoch_time_ms,
            label_tag=str(epoch_time_ms),
        )
        root_segment_in_db = SegmentInDB.from_segment_create(root_segment)
        self._save2graphdb(root_segment_in_db)
        doc_postion_map[ROOT_POSITION] = root_segment_in_db.graph_node_id

        self._update_doc_graph(doc_postion_map)
        return rtn_code

    def split(
        self, doc: Document, log_file_location: Optional[str] = None
    ) -> ReturnCode:
        if log_file_location:
            log_handler = logger().log_to_file(log_file_location)
        else:
            log_handler = None
        try:
            rtn_code = self._split(doc)
            return rtn_code
        except Exception as e:
            trace = traceback.format_exc()
            err_str = f"{trace}"
            if "Number of parts exceeds the number of words in the text" in err_str:
                logger().error(
                    f"Error splitting document [possible binary data]: {trace}"
                )
                return ReturnCode.FAILURE_ABORT
            logger().error(f"Error splitting document: {trace}")
            return ReturnCode.FAILURE
        finally:
            if log_handler:
                logger().remove_file_handler()
