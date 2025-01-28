from typing import Any, Dict, Optional

from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.str_embedder._impl.splade_function import SpladeFunction
from leettools.eds.str_embedder.schemas.schema_sparse_embedder import (
    SparseEmbeddingRequest,
    SparseEmbeddings,
)
from leettools.eds.str_embedder.sparse_embedder import (
    SPARSE_EMBED_PARAM_MODEL,
    AbstractSparseEmbedder,
)
from leettools.settings import SystemSettings


class SparseStrEmbedderSplade(AbstractSparseEmbedder):

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        if kb is None:
            model_name = context.settings.DEFAULT_SPLADE_EMBEDDING_MODEL
        else:
            if kb.sparse_embedder_params is None:
                model_name = context.settings.DEFAULT_SPLADE_EMBEDDING_MODEL
            else:
                model_name = kb.sparse_embedder_params[SPARSE_EMBED_PARAM_MODEL]
                if model_name is None:
                    model_name = context.settings.DEFAULT_SPLADE_EMBEDDING_MODEL
        self.splade_ef = SpladeFunction().get_function(model_name)

    def embed(self, embed_requests: SparseEmbeddingRequest) -> SparseEmbeddings:
        logger().info(
            f"Embedding sentences using SPLADEEmbedder {len(embed_requests.sentences)} ..."
        )
        rtn_list = self.splade_ef.encode_documents(embed_requests.sentences)
        logger().info(
            f"Finshed embedding sentences using SPLADEEmbedder {len(embed_requests.sentences)} ..."
        )
        return SparseEmbeddings(sparse_embeddings=rtn_list)

    def get_dimension(self) -> int:
        return self.splade_ef.dim

    @classmethod
    def get_default_params(cls, settings: SystemSettings) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        params[SPARSE_EMBED_PARAM_MODEL] = settings.DEFAULT_SPLADE_EMBEDDING_MODEL
        return params
