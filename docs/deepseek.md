# Using DeepSeek API

We can also use any OpenAI-compatible LLM inference endpoint by setting the related 
environment variable. For example, we can use the DeepSeek API by setting the following
environment variables:

```bash
### to use other API providers such as DeepSeek, you can
% export EDS_DEFAULT_OPENAI_BASE_URL=https://api.deepseek.com/v1
% export EDS_OPENAI_API_KEY=<your deepseek api key>
% export EDS_DEFAULT_OPENAI_MODEL=deepseek-chat
# use a local embedder since DeepSeek does not provide an embedding endpoint yet
# if the API supports OpenAI-compatible embedding endpoint, no extra settings needed
# this dense_embedder_local_mem uses all-MiniLM-L6-v2 model as a singleton embedder
% export EDS_DEFAULT_DENSE_EMBEDDER=dense_embedder_local_mem

# Or you can put the above settings in the .env.deepseek file
% cat .env.deepseek
LEET_HOME=/Users/myhome/leettools
EDS_DEFAULT_OPENAI_BASE_URL=https://api.deepseek.com/v1
EDS_OPENAI_API_KEY=sk-0d8-mykey
EDS_DEFAULT_OPENAI_MODEL=deepseek-chat
EDS_DEFAULT_DENSE_EMBEDDER=dense_embedder_local_mem

# Then run the command with the -e option to specify the .env file to use
% leet flow -e .env.deepseek -t answer -q "How does GraphRAG work?" -k graphrag -l info
```