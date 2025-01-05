from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import create_model

from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.rag.search.filter import BaseCondition, Filter

EXTRACT_DB_METADATA_FIELD = "eds_metadata"
EXTRACT_DB_SOURCE_FIELD = "eds_source_uri"
EXTRACT_DB_TIMESTAMP_FIELD = "created_timestamp_in_ms"


class AbstractExtractStore(ABC):
    """
    This class is an abstract class for the extract store, whose is responsible for
    saving, getting, and deleting records from the extract store.
    """

    def __init__(
        self,
        context: Context,
        org: Org,
        kb: KnowledgeBase,
        target_model_name: str,
        target_model_class: Type[TypeVar_BaseModel],
    ):
        self.context = context
        self.org = org
        self.kb = kb
        self.target_model_name = target_model_name
        self.target_model_class = target_model_class

    @abstractmethod
    def save_records(
        self, records: List[TypeVar_BaseModel], metadata: Dict[str, Any]
    ) -> List[TypeVar_BaseModel]:
        """
        Save a list of target records to the extract store. The schema has to match
        the type specified in the target_model_class in the constructor. A new field
        'created_timestamp_in_ms' will be added to the record and extra metadata can
        be added to the record through the metadata parameter. Right now the 'eds_source_uri'
        field is added to the record to connect the record to the source if provided
        in the metadata.

        Args:
        - records: The list of records in the orginal schema to save.
        - metadata: The metadata to add to the records.

        Returns:
        - The list of records in the extended schema.
        """
        pass

    @abstractmethod
    def get_records(
        self, filter: Optional[Union[Filter, BaseCondition]] = None
    ) -> List[TypeVar_BaseModel]:
        """
        Get the records from the extract store. The schema of the records will be the
        extended schema with the 'eds_metadata' and 'created_timestamp_in_ms' fields.

        Args:
        - filter: The filter to apply to the records. None means no filter.

        returns:
        - The list of records in the extended schema.
        """
        pass

    @abstractmethod
    def delete_records(
        self, filter: Optional[Union[Filter, BaseCondition]] = None
    ) -> None:
        """
        Delete the records from the extract store. None filter means delete all records.

        Args:
        - filter: The filter to apply to the records. None means no filter.

        Returns:
        - None
        """
        pass

    @abstractmethod
    def get_actual_model(self) -> Type[TypeVar_BaseModel]:
        """
        Get the actual model class that the extract store is using. Usually added
        with the 'eds_metadata' and 'created_timestamp_in_ms' fields.
        """
        pass


def create_extract_store(
    context: Context,
    org: Org,
    kb: KnowledgeBase,
    target_model_name: str,
    target_model_class: Type[TypeVar_BaseModel],
) -> AbstractExtractStore:
    from leettools.common.utils import factory_util

    settings = context.settings

    return factory_util.create_manager_with_repo_type(
        manager_name="extract_store",
        repo_type=settings.DOC_STORE_TYPE,
        base_class=AbstractExtractStore,
        context=context,
        org=org,
        kb=kb,
        target_model_name=target_model_name,
        target_model_class=target_model_class,
    )


def get_extended_model(
    target_model_name: str, model_class: Type[TypeVar_BaseModel]
) -> Type[TypeVar_BaseModel]:
    """
    Add a source and a created_timestamp_in_ms field to the model.
    """
    ExtendedModel = create_model(
        f"{target_model_name}_extended",
        eds_metadata=(Dict[str, Any], {}),
        eds_source_uri=(Optional[str], None),
        created_timestamp_in_ms=(int, ...),
        __base__=model_class,
    )
    return ExtendedModel
