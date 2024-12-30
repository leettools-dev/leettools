import os

from leettools.common.utils.obj_utils import ENV_VAR_PREFIX

if __name__ == "__main__":
    """
    This script can be used to download and cache the SPLADE model.
    """
    os.environ[f"{ENV_VAR_PREFIX}DATA_ROOT"] = "dummy"
    os.environ[f"{ENV_VAR_PREFIX}LOG_ROOT"] = "dummy"

    # put the imports after the dummy environment variables
    from leettools.context_manager import Context, ContextManager
    from leettools.eds.str_embedder._impl.sparse_embedder_splade import (
        SparseStrEmbedderSplade,
    )
    from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
        DenseEmbeddingRequest,
    )

    context = ContextManager().get_context()  # type: Context
    model_name = context.settings.DEFAULT_SPLADE_EMBEDDING_MODEL

    splade_embedder = SparseStrEmbedderSplade(model_name=model_name)
    embed_requests = DenseEmbeddingRequest(sentences=["hello world"])
    embeddings = splade_embedder.embed(embed_requests)
    print(embeddings)
    print(splade_embedder.get_dimension())
