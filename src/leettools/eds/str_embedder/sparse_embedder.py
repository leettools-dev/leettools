from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.str_embedder.schemas.schema_sparse_embedder import (
    SparseEmbeddingRequest,
    SparseEmbeddings,
)
from leettools.settings import SystemSettings

SPARSE_EMBED_PARAM_SVC = "service_endpoint"
SPARSE_EMBED_PARAM_MODEL = "model_name"
SPARSE_EMBED_PARAM_DIM = "model_dimension"


class AbstractSparseEmbedder(ABC):
    """
    An abstract class for embedding strings into vectors.

    This class defines the interface for embedding models or services.
    Subclasses must implement the abstract methods to perform the actual embedding work.
    """

    @abstractmethod
    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        pass

    @abstractmethod
    def embed(self, embed_requests: SparseEmbeddingRequest) -> SparseEmbeddings:
        """
        Embeds a single string or a batch of strings into vectors.

        Parameters:
            input_requests (EmbeddingRequest): The input data to be embedded.

        Returns:
            AbstractEmbeddings: The embeddings of the input data.
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Returns the dimension of the embedding vectors produced by the embedding model or service.

        Returns:
            int: The dimension of the embedding vectors.
        """
        pass

    @classmethod
    @abstractmethod
    def get_default_params(cls, settings: SystemSettings) -> Dict[str, Any]:
        """
        Returns the default parameters for the embedding model or service.

        Returns:
            dict: The default parameters for the embedding model or service.
        """
        pass


T_SparseEmbedder = TypeVar("T_SparseEmbedder", bound=AbstractSparseEmbedder)


def get_sparse_embedder_class(
    sparse_embedder: str, settings: SystemSettings
) -> T_SparseEmbedder:
    import os

    from leettools.common.utils import factory_util

    module_name = sparse_embedder
    if module_name is None or module_name == "":
        module_name = os.environ.get(SystemSettings.EDS_DEFAULT_SPARSE_EMBEDDER, None)
        if module_name is None or module_name == "":
            module_name = settings.DEFAULT_SPARSE_EMBEDDER

    if "." not in module_name:
        module_name = f"{__package__}._impl.{module_name}"

    base_class = AbstractSparseEmbedder
    subclasses = factory_util.get_subclass_from_module(module_name, base_class)
    if len(subclasses) == 0:
        raise exceptions.UnexpectedCaseException(
            f"No subclasses of {base_class} found in the module {module_name}"
        )
    elif len(subclasses) > 1:
        err_msg = ", ".join([cls.__name__ for cls in subclasses])
        logger().debug(
            f"More than one subclass of {base_class} found in the module {module_name}: {err_msg}."
            f"Using the first one: {subclasses[0].__name__}"
        )

    cls = subclasses[0]
    return cls


def create_sparse_embber_for_kb(
    org: Org, kb: KnowledgeBase, user: User, context: Context
) -> AbstractSparseEmbedder:
    """
    Get the sparse embedder for the knowledge base.

    Args:
    -   org: The organization to get the embedder for.
    -   kb: The knowledge base to get the embedder for.
    -   user: The user to get the embedder for, may need the user credential to call the service.
    -   context: The context to get the embedder for.

    Returns:
    -   The sparse embedder.
    """

    sparse_embedder_class = get_sparse_embedder_class(
        kb.sparse_embedder, context.settings
    )
    return sparse_embedder_class(
        org=org,
        kb=kb,
        user=user,
        context=context,
    )
