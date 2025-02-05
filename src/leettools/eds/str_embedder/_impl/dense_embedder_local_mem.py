from typing import Any, Dict, Optional

import click

from leettools.common.singleton_meta import SingletonMeta
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.str_embedder._impl.dense_embedder_sentence_transformer import (
    DenseEmbedderSentenceTransformer,
)
from leettools.eds.str_embedder.dense_embedder import (
    DENSE_EMBED_PARAM_MODEL,
    AbstractDenseEmbedder,
)
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)


class DenseEmbedderLocalMem(AbstractDenseEmbedder, metaclass=SingletonMeta):
    """
    A singleton wrapper that runa a local embedding model in memory.

    This is similar to the EmbedderLocalSvcClient but run the model in memory, which
    will be slower when starting up but you do not need to start the local service
    separately. The default local testing should use the EmbedderLocalSvcClient since
    startup is faster.
    """

    def __init__(
        self,
        context: Context,
        org: Optional[Org] = None,
        kb: Optional[KnowledgeBase] = None,
        user: Optional[User] = None,
    ):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            self.context = context
            self.embedder = DenseEmbedderSentenceTransformer(
                context=context, org=org, kb=kb, user=user
            )

    def embed(self, embed_requests: DenseEmbeddingRequest) -> DenseEmbeddings:
        return self.embedder.embed(embed_requests)

    def is_compatible_class(self, other: AbstractDenseEmbedder) -> bool:
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
        return self.embedder.get_model_name()

    def get_dimension(self) -> int:
        return self.embedder.get_dimension()

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


@click.command
@click.option(
    "-s",
    "--string",
    "input_string",
    required=True,
    help="The string to embed",
)
def embed(input_string: str):
    embedder = DenseEmbedderLocalMem()
    embed_request = DenseEmbeddingRequest(sentences=[input_string])
    embeddings = embedder.embed(embed_request)
    print(f"{embeddings.dense_embeddings[0]}")


if __name__ == "__main__":
    embed()
