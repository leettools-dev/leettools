import logging
from pathlib import Path
from typing import Optional, Tuple

import click

from eval.data_preprocess.config import (DEFAULT_FINANCEBENCH_PATH,
                                         DEFAULT_MEDICALBENCH_PATH)
from leettools.chat import chat_utils
from leettools.cli.cli_utils import setup_org_kb_user
from leettools.context_manager import ContextManager
from leettools.core.consts import flow_option
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.retriever_type import RetrieverType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.flow.exec_info import ExecInfo
from leettools.flow.utils import pipeline_utils


class IngestionManager:
    def __init__(
        self, 
        kb_name: str,
        context_name: str = "dataset_eval"
    ):
        self.kb_name = kb_name
        self.context_name = context_name
        self.logger = logging.getLogger(__name__)
        
        # Initialize context
        self.context = ContextManager().get_context()
        self.context.is_svc = False
        self.context.name = f"{self.context.EDS_CLI_CONTEXT_PREFIX}_{context_name}"
        
        # Get managers
        self.repo_manager = self.context.get_repo_manager()
        self.docsource_store = self.repo_manager.get_docsource_store()

    def run_ingestion(self, dataset: FinanceBenchDataset) -> Tuple[ExecInfo, str]:
        """Run ingestion process for FinanceBench dataset"""
        self.logger.info(f"Starting ingestion process for KB: {self.kb_name}")
        
        # Setup organization, KB and user
        org, kb, user = setup_org_kb_user(
            self.context, 
            None,  # org_name (will create default)
            self.kb_name,
            None   # username (will create default)
        )

        # Process each PDF document
        pdf_paths = dataset.get_document_paths()
        self.logger.info(f"Processing {len(pdf_paths)} PDF documents")

        for pdf_path in pdf_paths:
            try:
                self._process_document(org, kb, user, pdf_path)
            except Exception as e:
                self.logger.error(f"Error processing {pdf_path}: {e}")
                continue

        self.logger.info(f"Ingestion completed for KB: {self.kb_name}")
        
        # Use chat_utils to setup exec_info
        exec_info = chat_utils.setup_exec_info(
            context=self.context,
            query="dummy",  # You can set this to a relevant query if needed
            org_name=org.name,
            kb_name=self.kb_name,
            username=user.username,
            strategy_name=None,
            flow_options={
                flow_option.FLOW_OPTION_RETRIEVER_TYPE: RetrieverType.LOCAL,
            },
            display_logger=self.logger,  # Use the logger for display
        )
        
        return exec_info, self.kb_name

    def _process_document(self, org, kb, user, doc_path: Path) -> None:
        """Process a single document and add to knowledge base"""
        self.logger.info(f"Processing document: {doc_path}")
        
        # Create document source
        docsource_create = DocSourceCreate(
            org_id=org.org_id,
            kb_id=kb.kb_id,
            source_type=DocSourceType.LOCAL,
            uri=str(doc_path)
        )
        
        # Add document to knowledge base
        docsource = self.docsource_store.create_docsource(org, kb, docsource_create)
        
        # Process document through pipeline
        pipeline_utils.process_docsource_manual(
            org=org,
            kb=kb,
            user=user,
            docsource=docsource,
            context=self.context,
            display_logger=self.logger
        )

@click.command()
@click.option(
    "-d",
    "--domain",
    required=True,
    type=click.Choice(['finance', 'medical'], case_sensitive=False),
    help="Domain of the dataset (finance or medical)"
)
def run_ingestion_cli(domain: str):
    """Run ingestion process from command line"""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Set dataset path based on domain
    if domain.lower() == 'finance':
        dataset_path = DEFAULT_FINANCEBENCH_PATH
        from eval.data_preprocess.financebench_loader import \
            FinanceBenchDataset
        dataset = FinanceBenchDataset(dataset_path)
    elif domain.lower() == 'medical':
        dataset_path = DEFAULT_MEDICALBENCH_PATH
        dataset = None
        # from eval.data_preprocess.medicalbench_loader import MedicalBenchDataset
        # dataset = MedicalBenchDataset(dataset_path)
    else:
        raise ValueError("Invalid domain specified. Choose 'finance' or 'medical'.")

    # Load dataset
    # dataset = FinanceBenchDataset(dataset_path)
    
    # Automatically set KB name
    kb_name = f"{domain}_kb"
    
    # Run ingestion
    ingestion_manager = IngestionManager(kb_name=kb_name)
    exec_info, kb_name = ingestion_manager.run_ingestion(dataset)
    return exec_info

if __name__ == "__main__":
    run_ingestion_cli()