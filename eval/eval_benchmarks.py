import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from pydantic import BaseModel
from ragas.dataset_schema import EvaluationResult

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
from leettools.flow.exec_info import ExecInfo
from leettools.flow.utils import pipeline_utils

from .data_preprocess.base_dataset import BaseDataset
from .data_preprocess.financebench_loader import FinanceBenchDataset


class BenchmarkEvalResult(BaseModel):
    dataset_name: str
    eval_result: EvaluationResult
    metadata: Dict[str, Any] = {}

def run_ingestion(dataset: BaseDataset) -> ExecInfo:
    timestamp = time_utils.cur_timestamp_in_ms()
    kb_name = f"eval_benchmark_{timestamp}"

    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_eval_benchmark"

    repo_manager = context.get_repo_manager()
    docsource_store = repo_manager.get_docsource_store()

    display_logger = logger()

    org, kb, user = setup_org_kb_user(context, None, kb_name, None)

    # Process all documents from the dataset
    for doc_path in dataset.get_document_paths():
        docsource_create = DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.LOCAL,
            uri=str(doc_path),
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

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query="dummy",
        org_name=org.name,
        kb_name=kb_name,
        username=user.username,
        strategy_name=None,
        flow_options={
            flow_option.FLOW_OPTION_RETRIEVER_TYPE: RetrieverType.LOCAL,
        },
        display_logger=None,
    )
    return exec_info

def run_queries(dataset: BaseDataset, exec_info: ExecInfo) -> List[Dict[str, Any]]:
    context = exec_info.context
    chat_manager = get_history_manager(context)
    eval_dataset: List[Dict[str, Any]] = []

    for question_item in dataset.get_questions():
        query = question_item.question
        reference = question_item.expected_answer

        exec_info.query = query
        exec_info.target_chat_query_item.query_content = query

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

        eval_dataset.append({
            "user_input": query,
            "retrieved_contexts": relevant_docs,
            "response": response,
            "reference": reference,
        })
    
    return eval_dataset

def run_eval(dataset: List[Dict[str, Any]]) -> EvaluationResult:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas import EvaluationDataset, evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (FactualCorrectness, Faithfulness,
                               LLMContextRecall)

    # Use local embeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    evaluation_dataset = EvaluationDataset.from_list(dataset)

    # Configure local LLM (you'll need to implement this part based on your needs)
    from langchain_community.llms import LlamaCpp  # or other local LLM
    llm = LlamaCpp(
        model_path="path/to/your/local/model.gguf",
        temperature=0.1,
        max_tokens=2000,
        context_window=2048,
        # Add other parameters as needed
    )
    
    evaluator_llm = LangchainLLMWrapper(llm)
    
    result = evaluate(
        dataset=evaluation_dataset,
        metrics=[
            LLMContextRecall(),
            Faithfulness(),
            FactualCorrectness()
        ],
        llm=evaluator_llm,
    )
    return result

@click.command(help="Evaluate the pipeline with benchmark datasets.")
@click.option(
    "-d",
    "--dataset",
    "dataset_name",
    type=click.Choice(["financebench"]),
    required=True,
    help="The benchmark dataset to use for evaluation.",
)
@click.option(
    "-p",
    "--data-path",
    "data_path",
    required=True,
    help="Path to the dataset files.",
)
def eval_benchmark(dataset_name: str, data_path: str):
    # Load dataset based on name
    if dataset_name == "financebench":
        dataset = FinanceBenchDataset(data_path)
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    logger().info(f"Loading dataset: {dataset_name}")
    dataset.load()
    
    logger().info("Starting ingestion...")
    exec_info = run_ingestion(dataset)
    logger().info("Ingestion completed.")

    logger().info("Running queries...")
    eval_dataset = run_queries(dataset, exec_info)
    logger().info("Queries completed.")

    logger().info("Running evaluation...")
    result = run_eval(eval_dataset)
    logger().info("Evaluation completed.")

    # Save results
    benchmark_result = BenchmarkEvalResult(
        dataset_name=dataset_name,
        eval_result=result,
        metadata=dataset.get_metadata()
    )
    
    # Save results to file
    output_dir = Path("eval/results")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{dataset_name}_{time_utils.cur_timestamp_in_ms()}.json"
    output_file.write_text(benchmark_result.model_dump_json(indent=2))
    
    print(result)

if __name__ == "__main__":
    eval_benchmark() 