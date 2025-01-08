from typing import List

from pydantic import BaseModel, Field


class DenseEmbeddingRequest(BaseModel):
    """
    The input data model for the /encode/ endpoint.

    Right now it is only a list of strings, but we an add other request parameters in the future.
    """

    sentences: List[str] = Field(
        ...,
        title="input sentences",
        description="The list of strings to embed.",
    )


class DenseEmbeddings(BaseModel):
    """
    The response data model for the /encode/ endpoint.
    """

    dense_embeddings: List[List[float]] = Field(
        ...,
        title="dense embeddings",
        description="The list of returned embeddings, each one of which is a list of float.",
    )
