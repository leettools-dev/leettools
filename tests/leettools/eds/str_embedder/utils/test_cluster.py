from leettools.context_manager import ContextManager
from leettools.eds.str_embedder._impl.dense_embedder_sentence_transformer import (
    DenseEmbedderSentenceTransformer,
)
from leettools.eds.str_embedder.utils.cluster import cluster_strings


def test_cluster_string():
    sample_strings = [
        "apple",
        "banana",
        "apple fruit",
        "orange",
        "apple pie",
        "banana split",
        "citrus orange",
    ]

    result_01 = cluster_strings(sample_strings)
    print("==== Use Sentence-Transformer directly with default settings ====")
    print(result_01)

    context = ContextManager().get_context()
    embedder = DenseEmbedderSentenceTransformer(
        org=None, kb=None, user=None, context=context
    )
    result_02 = cluster_strings(sample_strings, embedder=embedder)
    print("==== Use DenseEmbedderSentenceTransformer as a wrapper ====")
    print(result_02)

    assert result_01 == result_02
