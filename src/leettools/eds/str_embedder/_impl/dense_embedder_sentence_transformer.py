from typing import Any, Dict, Optional

from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.str_embedder.dense_embedder import (
    DENSE_EMBED_PARAM_MODEL,
    AbstractDenseEmbedder,
)
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)


class DenseEmbedderSentenceTransformer(AbstractDenseEmbedder):
    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        from sentence_transformers import SentenceTransformer

        if kb is None:
            # default is all-MiniLM-L6-v2
            model_name = context.settings.DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME
        else:
            if kb.dense_embedder_params is None:
                model_name = context.settings.DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME
            else:
                model_name = kb.dense_embedder_params[DENSE_EMBED_PARAM_MODEL]
                if model_name is None:
                    model_name = (
                        context.settings.DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME
                    )

        logger().info(f"Loading dense embedder model {model_name}...")
        # TODO: allow SentenceTransformer to more parameters
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        embeddings = self.model.encode("")
        self.embedding_dimension = len(embeddings.tolist())

    def embed(self, embed_requests: DenseEmbeddingRequest) -> DenseEmbeddings:
        results: DenseEmbeddings = DenseEmbeddings(dense_embeddings=[])
        for sentence in embed_requests.sentences:
            # TODO: allow the encode function to take extra parameters
            results.dense_embeddings.append(self.model.encode(sentence).tolist())
        return results

    def is_compatible_class(self, other: AbstractDenseEmbedder) -> bool:
        from leettools.eds.str_embedder._impl.dense_embedder_local_mem import (
            DenseEmbedderLocalMem,
        )
        from leettools.eds.str_embedder._impl.dense_embedder_local_svc_client import (
            DenseEmbedderLocalSvcClient,
        )

        if (
            isinstance(other, DenseEmbedderLocalMem)
            or isinstance(other, DenseEmbedderLocalSvcClient)
            or isinstance(other, DenseEmbedderSentenceTransformer)
        ):
            return True

        return False

    def get_model_name(self) -> str:
        return self.model_name

    def get_dimension(self) -> int:
        return self.embedding_dimension

    @classmethod
    def get_default_params(cls, context: Context, user: User) -> Dict[str, Any]:
        if user is None:
            user = User.get_admin_user()
        settings = context.settings
        user_settings_store = context.get_user_settings_store()
        user_settings = user_settings_store.get_settings_for_user(user)
        params: Dict[str, Any] = {}

        if context.is_svc:
            params[DENSE_EMBED_PARAM_MODEL] = user_settings.get_value(
                key="DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME",
                default_value=settings.DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME,
            )
        else:
            value = settings.DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME
            if value is None or value == "":
                value = user_settings.get_value(
                    key="DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME",
                    default_value="sentence-transformers/all-MiniLM-L6-v2",
                )
            params[DENSE_EMBED_PARAM_MODEL] = value

        return params
