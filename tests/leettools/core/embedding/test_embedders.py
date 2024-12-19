from leettools.context_manager import ContextManager
from leettools.eds.str_embedder._impl.dense_embedder_local_mem import (
    DenseEmbedderLocalMem,
)
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
)


def test_local_embedder():
    # Initialize the LocalModelEmbedder singleton
    context = ContextManager().get_context()
    embedder = DenseEmbedderLocalMem(org=None, kb=None, user=None, context=context)

    # Example string for embedding
    test_string = "hello"
    test_request = DenseEmbeddingRequest(sentences=[test_string])

    # Embed a single string
    result = embedder.embed(test_request)
    assert len(result.dense_embeddings) == 1
    assert len(result.dense_embeddings[0]) == embedder.get_dimension()

    # Example list of strings for batch embedding
    test_strings = ["hello", "world", "python", "embed"]
    test_batch_request = DenseEmbeddingRequest(sentences=test_strings)
    # Embed a batch of strings
    batch_results = embedder.embed(test_batch_request)
    assert len(batch_results.dense_embeddings) == len(test_strings)
    for emb in batch_results.dense_embeddings:
        assert len(emb) == embedder.get_dimension()

    # Demonstrate that the embedder is indeed a singleton by creating another instance
    another_embedder = DenseEmbedderLocalMem()
    assert embedder is another_embedder
