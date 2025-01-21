# Using DeepSeek API

We can also use any OpenAI-compatible LLM inference endpoint by setting the related 
environment variable. For example, we can use the DeepSeek API by setting the following
environment variables:

```bash
### to you can put the settings in the .env.deepseek file
% cat > .env.deepseek <<EOF
LEET_HOME=</Users/myhome/leettools>
EDS_DEFAULT_LLM_BASE_URL=https://api.deepseek.com/v1
EDS_LLM_API_KEY=<sk-0d8-mykey>
EDS_DEFAULT_INFERENCE_MODEL=deepseek-chat
EDS_DEFAULT_DENSE_EMBEDDER=dense_embedder_local_mem
EOF

# Then run the command with the -e option to specify the .env file to use
% leet flow -e .env.deepseek -t answer -q "How does GraphRAG work?" -k graphrag -l info
```

The "EDS_DEFAULT_DENSE_EMBEDDER" setting specifies to use a local embedder with a default
all-MiniLM-L6-v2 model since DeepSeek does not provide an embedding endpoint yet. If the
API supports OpenAI-compatible embedding endpoint, no extra setting is needed. 

If you want to use another API provider (OpenAI compatible) for embedding, say a local
Ollama embedder, you can set the embedding endpoint URL and API key separately as follows:

```bash
% cat > .env.deepseek <<EOF
LEET_HOME=</Users/myhome/leettools>
EDS_DEFAULT_LLM_BASE_URL=https://api.deepseek.com/v1
EDS_LLM_API_KEY=<sk-0d8-mykey>
EDS_DEFAULT_INFERENCE_MODEL=deepseek-chat

# this specifies to use an OpenAI compatible embedding endpoint
EDS_DEFAULT_DENSE_EMBEDDER=dense_embedder_openai

# the following specifies the embedding endpoint URL and model to use
EDS_DEFAULT_EMBEDDING_BASE_URL=http://localhost:11434/v1
EDS_EMBEDDING_API_KEY=dummy-key
EDS_DEFAULT_EMBEDDING_MODEL=nomic-embed-text
EDS_EMBEDDING_MODEL_DIMENSION=768
EOF
```
