All embedding operations should use the AbstractStringEmbedder abstract class as the following:

```python

embedder : AbstractStringEmbedder = LocalEmbedder()
embed_request = EmbedRequest(sentences=["text1", "text2"])
embed_result = embedder.embed(embed_request)
print(embed_result.embeddings[0]) # this is the result for "text1"
```

We can set the EMBEDDING_SERVICE_TYPE settings variable to control the behavior:

- If the value is the default value "MEM", the default embeder is the LocalEmbedder singleton object, which uses the SentenceTransformerEmbedder class to load the model "all-MiniLM-L6-v2" into memory and provide service. Although it loads the model only once, it is still pretty slow at startup.
- We can start a local service that runs the SentenceTransformerEmbedder as a service and use its API to do the embedding work. The service can either run on the same host or a different one.

```bash
# by default this starts the service on 8001
python src/embedding/local_embdedding_service.py
export EMBEDDING_SERVICE_TYPE="LOCAL"
export EMBEDDING_SERVICE_ENDPOINT="http://127.0.0.1:8001/api/v1/embed"
```

After the above setting, the embedder will use the local service to do the embedding work.

- TODO: we can set EMBEDDING_SERVICE_TYPE to "OPENAI" or other providers and use the correct client to do the embedding work. All we need to do is provide a client wrapper implementing the AbstractStringEmbedder interface, like the example in LocalEmbeddingServiceClient.
