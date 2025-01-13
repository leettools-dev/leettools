import tempfile
from pathlib import Path
from typing import List

from leettools.chat import chat_utils
from leettools.chat.history_manager import get_history_manager
from leettools.cli.cli_utils import setup_org_kb_user
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.context_manager import Context, ContextManager
from leettools.core.consts import flow_option
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.flow.utils import pipeline_utils

sample_docs = [
    "Albert Einstein proposed the theory of relativity, which transformed our understanding of time, space, and gravity.",
    "Marie Curie was a physicist and chemist who conducted pioneering research on radioactivity and won two Nobel Prizes.",
    "Isaac Newton formulated the laws of motion and universal gravitation, laying the foundation for classical mechanics.",
    "Charles Darwin introduced the theory of evolution by natural selection in his book 'On the Origin of Species'.",
    "Ada Lovelace is regarded as the first computer programmer for her work on Charles Babbage's early mechanical computer, the Analytical Engine.",
]

sample_queries = [
    "Who introduced the theory of relativity?",
    "Who was the first computer programmer?",
    "What did Isaac Newton contribute to science?",
    "Who won two Nobel Prizes for research on radioactivity?",
    "What is the theory of evolution by natural selection?",
]

expected_responses = [
    "Albert Einstein proposed the theory of relativity, which transformed our understanding of time, space, and gravity.",
    "Ada Lovelace is regarded as the first computer programmer for her work on Charles Babbage's early mechanical computer, the Analytical Engine.",
    "Isaac Newton formulated the laws of motion and universal gravitation, laying the foundation for classical mechanics.",
    "Marie Curie was a physicist and chemist who conducted pioneering research on radioactivity and won two Nobel Prizes.",
    "Charles Darwin introduced the theory of evolution by natural selection in his book 'On the Origin of Species'.",
]

dataset = []

timestamp = time_utils.cur_timestamp_in_ms()
kb_name = f"eval_{timestamp}"

context = ContextManager().get_context()  # type: Context
context.is_svc = False
context.name = "eval"

repo_manager = context.get_repo_manager()
docsource_store = repo_manager.get_docsource_store()
document_store = repo_manager.get_document_store()
chat_manager = get_history_manager(context)
display_logger = logger()

org, kb, user = setup_org_kb_user(context, None, kb_name, None)
org_name = org.name
username = user.username

with tempfile.TemporaryDirectory() as temp_dir:
    tmp_path = Path(temp_dir)
    print(f"Temporary path created: {tmp_path}")

    file_id: int = 1
    file_paths: List[Path] = []
    for doc in sample_docs:
        file_path = tmp_path / f"doc_{file_id}.txt"
        file_path.write_text(doc)
        file_id += 1
        file_paths.append(file_path)

    docsource_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        source_type=DocSourceType.LOCAL,
        uri=str(tmp_path),
    )
    docsource = docsource_store.create_docsource(org, kb, docsource_create)
    pipeline_utils.process_docsource_manual(
        org=org,
        kb=kb,
        user=user,
        docsource=docsource,
        context=context,
        display_logger=display_logger,
    )

    for query, reference in zip(sample_queries, expected_responses):
        exec_info = chat_utils.setup_exec_info(
            context=context,
            query=query,
            org_name=org.name,
            kb_name=kb_name,
            username=username,
            strategy_name=None,
            flow_options={
                flow_option.FLOW_OPTION_RETRIEVER_TYPE: RetrieverType.LOCAL,
            },
            display_logger=None,
        )

        chat_query_result = chat_manager.run_query_with_strategy(
            org=exec_info.org,
            kb=exec_info.kb,
            user=exec_info.user,
            chat_query_item_create=exec_info.target_chat_query_item,
            chat_query_options=exec_info.chat_query_options,
            strategy=exec_info.strategy,
        )

        relevant_docs = []
        cai = chat_query_result.chat_answer_item_list[0]
        response = cai.answer_content
        for citation in cai.answer_source_items.values():
            relevant_docs.append(citation.answer_source.source_content)

        dataset.append(
            {
                "user_input": query,
                "retrieved_contexts": relevant_docs,
                "response": response,
                "reference": reference,
            }
        )


from ragas import EvaluationDataset

evaluation_dataset = EvaluationDataset.from_list(dataset)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper

llm = ChatOpenAI(model="gpt-4o-mini")
embeddings = OpenAIEmbeddings()

evaluator_llm = LangchainLLMWrapper(llm)
from ragas.metrics import FactualCorrectness, Faithfulness, LLMContextRecall

result = evaluate(
    dataset=evaluation_dataset,
    metrics=[LLMContextRecall(), Faithfulness(), FactualCorrectness()],
    llm=evaluator_llm,
)
print(result)
