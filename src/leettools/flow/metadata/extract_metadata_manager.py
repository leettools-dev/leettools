from abc import ABC, abstractmethod
from typing import Dict, List

from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.flow.schemas.extract_metadata import ExtractMetadata
from leettools.settings import SystemSettings


class AbstractExtractMetadataManager(ABC):
    """
    This is the abstract class to manage the extraction metadata.
    """

    @abstractmethod
    def __init__(self, settings: SystemSettings) -> None:
        pass

    @abstractmethod
    def add_extracted_db_info(
        self, org: Org, kb: KnowledgeBase, info: ExtractMetadata
    ) -> None:
        """
        Adds extracted db info to the knowledge base.

        Args:
        - org: The organization object.
        - kb: The knowledge base object.
        - info: The extraction info object.

        Returns:
        - None
        """
        pass

    @abstractmethod
    def get_extracted_db_info(
        self, org: Org, kb: KnowledgeBase
    ) -> Dict[str, List[ExtractMetadata]]:
        """
        Retrieve the extracted database information for a given org and KB.

        Args:
        - org (Org): The organization object.
        - kb (KnowledgeBase): The knowledge base object.

        Returns:
        - Dict[str, List[ExtractionInfo]]: A dictionary containing the extracted
            database information, where the keys are the names of the tables and
            the values are lists of ExtractionInfo objects since we may have multiple
            extractions for a single table.
        """
        pass


def create_extraction_metadata_manager(
    settings: SystemSettings,
) -> AbstractExtractMetadataManager:
    from leettools.common.utils import factory_util

    return factory_util.create_manager_with_repo_type(
        manager_name="extract_metadata_manager",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractExtractMetadataManager,
        settings=settings,
    )
