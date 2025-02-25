import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
from ragas.dataset_schema import EvaluationResult

# from eval.data_preprocess.base_dataset import EvalItem
from eval.data_preprocess.base_dataset import QuestionItem
from eval.data_preprocess.config import (DEFAULT_FINANCEBENCH_PATH,
                                         DEFAULT_MEDICALBENCH_PATH)
from eval.data_preprocess.financebench_loader import FinanceBenchDataset
from leettools.chat import chat_utils
from leettools.chat.history_manager import get_history_manager
from leettools.cli.cli_utils import setup_org_kb_user
from leettools.context_manager import Context, ContextManager
from leettools.core.consts import flow_option
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.flow.exec_info import ExecInfo
from leettools.flow.utils import pipeline_utils


def setup_context(context_name: str = "dataset_eval") -> Context:
    """Setup and return the context for ingestion"""
    context = ContextManager().get_context()
    context.is_svc = False
    context.name = f"{context.EDS_CLI_CONTEXT_PREFIX}_{context_name}"
    return context

def process_document(context: Context, org, kb, user, doc_path: Path, logger) -> None:
    """Process a single document and add to knowledge base"""
    logger.info(f"Processing document: {doc_path}")
    
    docsource_store = context.get_repo_manager().get_docsource_store()
    
    # Create document source
    docsource_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb.kb_id,
        source_type=DocSourceType.LOCAL,
        uri=str(doc_path)
    )
    
    # Add document to knowledge base
    docsource = docsource_store.create_docsource(org, kb, docsource_create)
    
    # Process document through pipeline
    pipeline_utils.process_docsource_manual(
        org=org,
        kb=kb,
        user=user,
        docsource=docsource,
        context=context,
        display_logger=logger
    )

def setup_exec_info(kb_name: str, context: Optional[Context] = None, logger: Optional[logging.Logger] = None) -> ExecInfo:
    """Setup execution info for both ingestion and query processes
    
    Args:
        kb_name: Name of the knowledge base
        context: Optional existing context. If None, creates new context
        logger: Optional logger instance
    
    Returns:
        ExecInfo: Configured execution info
    """
    if context is None:
        context = setup_context()
    
    # Setup organization, KB and user
    org, kb, user = setup_org_kb_user(
        context, 
        None,  # org_name (will create default)
        kb_name,
        None   # username (will create default)
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
        display_logger=logger,
    )
    
    return exec_info

def run_ingestion(kb_name: str, pdf_paths: List[Path]) -> None:
    """Run ingestion process for dataset"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting ingestion process for KB: {kb_name}")
    
    # Setup context
    context = setup_context()
    
    # Setup organization, KB and user
    org, kb, user = setup_org_kb_user(
        context, 
        None,  # org_name (will create default)
        kb_name,
        None   # username (will create default)
    )

    # Process each PDF document
    # pdf_paths = dataset.get_document_paths()
    logger.info(f"Processing {len(pdf_paths)} PDF documents")

    for pdf_path in pdf_paths:
        try:
            process_document(context, org, kb, user, pdf_path, logger)
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            continue

    logger.info(f"Ingestion completed for KB: {kb_name}")

def run_queries(eval_data: QuestionItem, exec_info: ExecInfo) -> List[Dict[str, Any]]:

    context = exec_info.context
    chat_manager = get_history_manager(context)
    llm_result_dataset: List[Dict[str, Any]] = []

    for eval_data_item in eval_data:

        query = eval_data_item.question
        reference = eval_data_item.expected_answer

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

        llm_result_dataset.append(
            {
                "user_input": query,
                "retrieved_contexts": relevant_docs,
                "response": response,
                "reference": reference,
            }
        )
    return llm_result_dataset


def run_eval(dataset: List[Dict[str, Any]]) -> EvaluationResult:
    from ragas import EvaluationDataset

    evaluation_dataset = EvaluationDataset.from_list(dataset)

    from langchain_openai import ChatOpenAI
    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper

    llm = ChatOpenAI(model="gpt-4o-mini")
    evaluator_llm = LangchainLLMWrapper(llm)
    from ragas.metrics import (FactualCorrectness, Faithfulness,
                               LLMContextRecall)

    result = evaluate(
        dataset=evaluation_dataset,
        metrics=[LLMContextRecall(), Faithfulness(), FactualCorrectness()],
        llm=evaluator_llm,
    )
    return result

@click.command()
@click.option(
    "-d",
    "--domain",
    required=True,
    type=click.Choice(['finance', 'medical'], case_sensitive=False),
    help="Domain of the dataset (finance or medical)"
)
@click.option(
    "-i",
    "--ingesting-documents",
    "ingesting_documents",
    is_flag=True,
    required=False,
    help="Ingesting documents takes a long time, please firstly run it before querying and evaluating"  
)
@click.option(
    "-n",
    "--number-of-questions",
    "number_of_questions",
    type=int,
    default=None,
    required=False,
    help="Number of questions to evaluate"
)
def orchestrate_eval(domain: str, ingesting_documents: bool, number_of_questions: Optional[int]):
    """Run ingestion process from command line"""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Set dataset path based on domain
    if domain.lower() == 'finance':
        dataset_path = DEFAULT_FINANCEBENCH_PATH
        from eval.data_preprocess.financebench_loader import \
            FinanceBenchDataset
        source_dataset = FinanceBenchDataset(dataset_path)
    elif domain.lower() == 'medical':
        dataset_path = DEFAULT_MEDICALBENCH_PATH
        source_dataset = None
        # from eval.data_preprocess.medicalbench_loader import MedicalBenchDataset
        # dataset = MedicalBenchDataset(dataset_path)
    else:
        raise ValueError("Invalid domain specified. Choose 'finance' or 'medical'.")
    
    # Automatically set KB name
    kb_name = f"{domain}_kb"

    # Limit number of questions if specified
    if number_of_questions is not None:
        source_dataset.questions_df = source_dataset.questions_df.head(number_of_questions)
        logger.info(f"Limited evaluation to {number_of_questions} questions")
    
    if ingesting_documents:
        # Only run ingestion
        logger.info("Starting ingestion process...")
        run_ingestion(kb_name, list(set(source_dataset.get_document_paths())))
        logger.info("Ingestion completed")
    else:
        # Run query and evaluation
        logger.info("Starting query and evaluation process...")
        
        # Setup exec_info for querying
        exec_info = setup_exec_info(kb_name, logger=logger)
        
        # Run queries
        logger.info("Running queries...")
        llm_result_dataset = run_queries(source_dataset.get_questions(),exec_info)
        logger.info("Queries completed")
        
        # Run evaluation
        logger.info("Running evaluation...")
        eval_metric_result = run_eval(llm_result_dataset)
        logger.info("Evaluation completed")
        
        # Print results
        print("\nEvaluation Results:")
        print(eval_metric_result)

if __name__ == "__main__":
    orchestrate_eval()