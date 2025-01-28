from typing import Any, Dict, Optional

import requests

from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.str_embedder.dense_embedder import (
    DENSE_EMBED_PARAM_MODEL,
    DENSE_EMBED_PARAM_SVC,
    AbstractDenseEmbedder,
)
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)
from leettools.settings import SystemSettings


class DenseEmbedderLocalSvcClient(AbstractDenseEmbedder):
    """
    A client class for interacting with a local embedding service.

    Args:
    -   settings (SystemSettings): The system settings object containing the embedding service endpoint.

    Attributes:
    -   endpoint (str): The endpoint URL of the embedding service.
    -   dimension (int): The dimension of the embeddings.

    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        self.context = context
        if kb is None or kb.dense_embedder_params is None:
            self.endpoint = context.settings.DEFAULT_DENSE_EMBEDDING_SERVICE_ENDPOINT
        else:
            self.endpoint = kb.dense_embedder_params[DENSE_EMBED_PARAM_SVC]
        self.dimension = None

    def embed(self, embed_requests: DenseEmbeddingRequest) -> DenseEmbeddings:
        response = requests.post(self.endpoint, json=embed_requests.model_dump())
        if response.status_code == 200:
            try:
                embeddings = DenseEmbeddings.model_validate(response.json())
                return embeddings
            except Exception as e:
                raise Exception(
                    f"The return value {response} can't be validated: {str(e)}"
                )
        else:
            raise Exception(
                f"Failed to embed strings. Status code: {response.status_code}"
            )

    def is_compatible_class(self, other: AbstractDenseEmbedder) -> bool:
        from leettools.eds.str_embedder._impl.dense_embedder_local_mem import (
            DenseEmbedderLocalMem,
        )
        from leettools.eds.str_embedder._impl.dense_embedder_sentence_transformer import (
            DenseEmbedderSentenceTransformer,
        )

        if (
            isinstance(other, DenseEmbedderLocalMem)
            or isinstance(other, DenseEmbedderLocalSvcClient)
            or isinstance(other, DenseEmbedderSentenceTransformer)
        ):
            return True

        return False

    def get_model_name(self) -> str:
        try:
            response = requests.get(self.endpoint)
            if response.status_code == 200:
                model_name = response.json()["model_name"]
                return model_name
            else:
                raise Exception(
                    f"Failed to embed strings. Status code: {response.status_code}"
                )
        except Exception as e:
            logger().error(f"Failed to get model name: {str(e)}")
            return ""

    def get_dimension(self) -> int:
        if self.dimension is not None:
            return self.dimension

        embedding_request = DenseEmbeddingRequest(sentences=["test"])
        embeddings = self.embed(embedding_request)
        self.dimension = len(embeddings.dense_embeddings[0])
        return self.dimension

    @classmethod
    def get_default_params(cls, settings: SystemSettings) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        params[DENSE_EMBED_PARAM_SVC] = (
            settings.DEFAULT_DENSE_EMBEDDING_SERVICE_ENDPOINT
        )
        params[DENSE_EMBED_PARAM_MODEL] = (
            settings.DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME
        )
        return params
