from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)
from leettools.settings import SystemSettings

DENSE_EMBED_PARAM_SVC = "service_endpoint"
DENSE_EMBED_PARAM_MODEL = "model_name"
DENSE_EMBED_PARAM_DIM = "model_dimension"


class AbstractDenseEmbedder(ABC):
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
    def embed(self, embed_requests: DenseEmbeddingRequest) -> DenseEmbeddings:
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

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Returns the model name of the embedding model or service.

        Returns:
        - str: The model name of the embedding model or service.
        """
        pass

    def is_compatible_class(self, other: "AbstractDenseEmbedder") -> bool:
        """
        Check if the other embedder class is compatible with this embedder class.
        By default only the same class is compatible.

        Args:
        - other: The other embedder to check compatibility with.

        Returns:
        - True if the other embedder is compatible with this embedder, False otherwise.
        """
        if other is None:
            return False

        if self.__class__ == other.__class__:
            return True

        return isinstance(other, self.__class__)

    def is_compatible(self, other: "AbstractDenseEmbedder") -> bool:
        """
        Check if the other embedder is compatible with this embedder.

        Args:
        - other: The other embedder to check compatibility with.

        Returns:
        - True if the other embedder is compatible with this embedder, False otherwise.
        """
        if not self.is_compatible_class(other):
            return False

        if other.get_dimension() != self.get_dimension():
            return False

        if other.get_model_name() != self.get_model_name():
            return False

        return True

    @classmethod
    @abstractmethod
    def get_default_params(cls, context: Context, user: User) -> Dict[str, Any]:
        """
        Returns the default parameters for the embedding model or service. If no user
        settings are found, use the system default settings.

        Returns:
        - dict: The default parameters for the embedding model or service.
        """
        pass


T_DenseEmbedder = TypeVar("T_DenseEmbedder", bound=AbstractDenseEmbedder)


def get_dense_embedder_class(
    dense_embedder: str, settings: SystemSettings
) -> T_DenseEmbedder:
    import os

    from leettools.common.utils import factory_util

    module_name = dense_embedder
    if module_name is None or module_name == "":
        module_name = os.environ.get(SystemSettings.EDS_DEFAULT_DENSE_EMBEDDER, None)
        if module_name is None or module_name == "":
            module_name = settings.DEFAULT_DENSE_EMBEDDER

    if "." not in module_name:
        module_name = f"{__package__}._impl.{module_name}"

    base_class = AbstractDenseEmbedder
    subclasses = factory_util.get_subclass_from_module(module_name, base_class)
    if len(subclasses) == 0:
        raise exceptions.UnexpectedCaseException(
            f"No subclasses of {base_class} found in the module {module_name}"
        )
    elif len(subclasses) > 1:
        err_msg = ", ".join([cls.__name__ for cls in subclasses])
        logger().debug(
            f"More than one subclass of {base_class} found in the module {module_name}: {err_msg}."
            f"Using the last one: {subclasses[0].__name__}"
        )

    cls = subclasses[0]
    return cls


def create_dense_embedder_for_kb(
    org: Org, kb: KnowledgeBase, user: User, context: Context
) -> AbstractDenseEmbedder:
    """
    Get the embedder for the knowledge base.

    Args:
    - org: The organization to get the embedder for.
    - kb: The knowledge base to get the embedder for.
    - user: The user to get the embedder for, may need the user credential to call the service.
    - context: The context to get the embedder for.

    Returns:
    -   The embedder.
    """

    dense_embedder_class = get_dense_embedder_class(kb.dense_embedder, context.settings)
    return dense_embedder_class(
        context=context,
        org=org,
        kb=kb,
        user=user,
    )
