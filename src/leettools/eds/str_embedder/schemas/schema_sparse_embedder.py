from typing import List

from pydantic import BaseModel, ConfigDict, Field
from scipy.sparse import csr_array


class SparseEmbeddingRequest(BaseModel):
    """
    The input data model for the /encode/ endpoint.

    Right now it is only a list of strings, but we an add other request parameters in the future.
    """

    sentences: List[str] = Field(
        ...,
        title="input sentcences",
        description="The list of strings to embed.",
    )


class SparseEmbeddings(BaseModel):
    """
    The response data model for the /encode/ endpoint.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sparse_embeddings: csr_array = Field(
        ...,
        title="sparse embeddings",
        description="The list of returned embeddings, a 2D CSR (Compressed Sparse Row) array format.",
    )
