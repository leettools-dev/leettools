from unittest.mock import patch

import requests

from leettools.common.logging import logger
from leettools.context_manager import ContextManager
from leettools.eds.str_embedder._impl.dense_embedder_local_svc_client import (
    DenseEmbedderLocalSvcClient,
)
from leettools.eds.str_embedder.schemas.schema_dense_embedder import (
    DenseEmbeddingRequest,
    DenseEmbeddings,
)
from leettools.settings import SystemSettings


def test_local_embedding_service_client_with_mock():
    # Create an instance of the LocalEmbeddingServiceClient
    context = ContextManager().get_context()
    settings = SystemSettings().initialize()
    settings.DEFAULT_DENSE_EMBEDDING_SERVICE_ENDPOINT = (
        f"http://127.0.0.1:8001{settings.API_V1_STR}/embed"
    )
    embedding_service_client = DenseEmbedderLocalSvcClient(
        org=None,
        kb=None,
        user=None,
        context=context,
    )

    # Test the embed method
    embed_requests = DenseEmbeddingRequest(sentences=["test"])
    with patch.object(requests, "post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "dense_embeddings": [[0.1, 0.2, 0.3]]
        }
        embeddings = embedding_service_client.embed(embed_requests)
        assert isinstance(embeddings, DenseEmbeddings)
        assert len(embeddings.dense_embeddings) == 1
        assert len(embeddings.dense_embeddings[0]) == 3

    # Test the get_dimension method
    with patch.object(embedding_service_client, "embed") as mock_embed:
        mock_embed.return_value = DenseEmbeddings(dense_embeddings=[[0.1, 0.2, 0.3]])
        dimension = embedding_service_client.get_dimension()
        assert dimension == 3


def test_local_embedding_service_client_with_service():
    # Create an instance of the LocalEmbeddingServiceClient
    # TODO: this will not work in a real unit test env because we have to start the service separately
    # we need to think of a way to use testcontainers or a setup with all the containers running before
    # the tests start, which enables us to run the tests without mocks.
    context = ContextManager().get_context()
    settings = context.settings
    settings.DEFAULT_DENSE_EMBEDDING_SERVICE_ENDPOINT = (
        f"http://127.0.0.1:8001{settings.API_V1_STR}/embed"
    )
    logger().info(
        "The endpoint is " + settings.DEFAULT_DENSE_EMBEDDING_SERVICE_ENDPOINT
    )
    embedding_service_client = DenseEmbedderLocalSvcClient(
        org=None,
        kb=None,
        user=None,
        context=context,
    )

    # Test the embed method
    embed_requests = DenseEmbeddingRequest(sentences=["test"])
    embeddings = embedding_service_client.embed(embed_requests)
    assert isinstance(embeddings, DenseEmbeddings)
    assert len(embeddings.dense_embeddings) == 1

    # Test the get_dimension method
    dimension = embedding_service_client.get_dimension()
    assert dimension == len(embeddings.dense_embeddings[0])
