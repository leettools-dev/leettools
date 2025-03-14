from enum import Enum


class SearcherType(str, Enum):
    SIMPLE = "simple"  # dense embeddings search only
    HYBRID = "hybrid"  # dense + sparse embeddings search
    BM25_DENSE = "bm25_dense"  # dense + BM25 search, dense vector store with BM25 only
