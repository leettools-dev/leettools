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


class SparseStrEmbedderSplade(AbstractSparseEmbedder):

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        self.model_name = None
        if kb is not None:
            if kb.sparse_embedder_params is not None:
                self.model_name = kb.sparse_embedder_params.get(
                    SPARSE_EMBED_PARAM_MODEL, None
                )
        if self.model_name is None:
            default_params = self.get_default_params(context, user)
            self.model_name = default_params[SPARSE_EMBED_PARAM_MODEL]
        self.splade_ef = SpladeFunction().get_function(self.model_name)

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
    def get_default_params(cls, context: Context, user: User) -> Dict[str, Any]:
        if user is None:
            user = User.get_admin_user()
        settings = context.settings
        user_settings_store = context.get_user_settings_store()
        user_settings = user_settings_store.get_settings_for_user(user)
        params: Dict[str, Any] = {}

        if context.is_svc:
            params[SPARSE_EMBED_PARAM_MODEL] = user_settings.get_value(
                key="DEFAULT_SPARSE_EMBEDDING_MODEL",
                default_value=settings.DEFAULT_SPLADE_EMBEDDING_MODEL,
            )
        else:
            value = settings.DEFAULT_SPLADE_EMBEDDING_MODEL
            if value is None or value == "":
                value = user_settings.get_value(
                    key="DEFAULT_SPARSE_EMBEDDING_MODEL",
                    default_value="naver/splade-cocondenser-selfdistil",
                )
            params[SPARSE_EMBED_PARAM_MODEL] = value

        return params
