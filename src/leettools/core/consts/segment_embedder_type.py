from enum import Enum


class SegmentEmbedderType(str, Enum):
    SIMPLE = "simple"  # dense embeddings only
    HYBRID = "hybrid"  # dense + sparse embeddings
