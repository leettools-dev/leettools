from typing import Dict, List, Optional

from leettools.eds.str_embedder.dense_embedder import AbstractDenseEmbedder
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
)


def cluster_strings(
    strings: List[str],
    embedder: Optional[AbstractDenseEmbedder] = None,
    eps: Optional[float] = 0.3,
    min_samples: Optional[int] = 1,
) -> Dict[int, List[str]]:
    """
    Clusters a list of strings based on semantic similarity using Sentence-Transformers and DBSCAN.

    Args:
    - strings (List[str]): A list of strings to be clustered.
    - embedder (AbstractDenseEmbedder, optional): The name of the dense string embedder.
            If none, use Sentence-Transformer with settings default.
    - eps (float, optional): The maximum distance between two samples for them to be
            considered in the same cluster. Lower values create more clusters. Default is 0.3.
    - min_samples (int, optional): The minimum number of samples required to form a cluster.
            Default is 1.

    Returns:
    - Dict[int, List[str]]: A dictionary where keys are cluster IDs and values are lists
            of clustered strings. Cluster ID `-1` represents outliers (if any).

    Example:
        >>> strings = ["apple", "banana", "apple fruit", "orange", "apple pie", "banana split", "citrus orange"]
        >>> cluster_strings(strings)
        {0: ['apple', 'apple fruit', 'apple pie'], 1: ['banana', 'banana split'], 2: ['orange', 'citrus orange']}
    """
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import DBSCAN

    # Load pre-trained Sentence-Transformer model
    if embedder is None:
        model_name = "all-MiniLM-L6-v2"
        model = SentenceTransformer(model_name)
        embeddings: np.ndarray = model.encode(strings)
    else:
        embeddig_requests = DenseEmbeddingRequest(sentences=strings)
        embeddings_results = embedder.embed(embeddig_requests)
        embeddings: np.ndarray = np.array(embeddings_results.dense_embeddings)

    # Perform DBSCAN clustering
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit(
        embeddings
    )
    cluster_labels: np.ndarray = clustering.labels_

    # Organize results into a dictionary
    clustered_strings: Dict[int, List[str]] = {}
    for string, cluster in zip(strings, cluster_labels):
        clustered_strings.setdefault(cluster, []).append(string)

    return clustered_strings
