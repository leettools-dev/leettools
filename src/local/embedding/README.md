# Local Embedding Service

This service provides a local embedding service that can be used to embed text into vectors
(called dense embeddings comparing to sparse embeddings such as SPLADE). The service is
based on the SentenceTransformer library, which provides a simple interface to embed text
into vectors. It can be used for local dev and testing purposes since using a
SentenceTransformer model can be slow to start up.

All string dense embedding operations should use the factor method to create the
embedder object as follows:

```python

context = ContextManager().get_context()

# the default name is "dense_embedder_openai"
# the default can be modified by the EDS_DEFAULT_DENSE_EMBEDDER env variable
# the class should be under src/leettools/eds/str_embedder/_impl/{dense_embedder_name}.py
dense_embedder_name = "dense_embedder_local_svc_client"

dense_embedder_class = get_dense_embedder_class(dense_embedder_name, context.settings)
# we need the org, kb, and user objects to create the embedder to check their settings
# leave them to None if the embedder class does not need them
# we do not need them for local_svc_client
embedder = dense_embedder_class(
    context=context,
    org=None,
    kb=None,
    user=None,
)

embed_request = DenseEmbeddingRequest(sentences=["text1", "text2"])
embed_result = embedder.embed(embed_request)
print(embed_result.embeddings[0]) # this is the result for "text1"
```

Right now we have the following embedder implementations:
- local_mem: use the SentenceTransformerEmbedder class to load the model as a singleton
- local_svc_client: call the local embedding service to do the embedding work
- openai: call an OpenAI-compatible API to do the embedding work
- qwen: call the Qwen API to do the embedding work
- sentence_transformers: use the SentenceTransformer library directly

For the local_svc_client embedder, we can also set the following environment variables:

```
EDS_DEFAULT_DENSE_EMBEDDING_LOCAL_MODEL_NAME=all-MiniLM-L6-v2
EDS_DEFAULT_DENSE_EMBEDDING_SERVICE_HOST=127.0.0.1
EDS_DEFAULT_DENSE_EMBEDDING_SERVICE_PORT=8001
```

To start the local embedding service, run the following command:

```bash
# by default this starts the service on http://127.0.0.1:8001
python src/local/embedding/local_embdedding_service.py >/dev/null 2>&1 &

export EDS_DEFAULT_DENSE_EMBEDDER=dense_embedder_local_svc_client

# now all the requests will be sent to the local embedding service
```
