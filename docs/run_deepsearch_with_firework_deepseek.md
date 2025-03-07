# Run DeepResearch with DeepSeek Models

Both OpenAI o1-pro model and Google Gemini 1.5-pro model provide the "DeepResearch"
function that allows users to generate a research report based on a query. The
"digest" flow from LeetTools provides a similar function that can work with any LLM
model that can perform text extract and summarize functions. In this tutorial, we will
use the DeepSeek model API from fireworks.ai as an example.

## Get a DeepSeek API key

To use the DeepSeek API, you can either host the model yourself or use the hosted
version from API providers. In this example, we will use the API endpoint provided by
fireworks.ai.

1. Go to the [fireworks.ai](https://fireworks.ai) website and sign up for an account.
2. After you have signed up, go to the API section and create a new API key.
3. Copy the API key and save it in a secure location.
4. The endpoint will be:
   - https://api.fireworks.ai/inference/v1
     and the model names will be
   - accounts/fireworks/models/deepseek-r1
   - accounts/fireworks/models/deepseek-v3

## Create an environment file

We will use the deepseek-r1 model in the example, but note that the full deepseek-r1
model is usually more expensive than the deepseek-v3 model. The benefit is that it can
show the thinking trace of the writing process, which may be useful in some cases.

```bash
% cat > .env.fireworks <<EOF
EDS_DEFAULT_LLM_BASE_URL=https://api.fireworks.ai/inference/v1
EDS_LLM_API_KEY=fw_3ZS**********pJr
EDS_DEFAULT_INFERENCE_MODEL=accounts/fireworks/models/deepseek-r1
EDS_DEFAULT_EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
EDS_EMBEDDING_MODEL_DIMENSION=768
EOF
```

If you are using another provider or model, change the values accordingly.

## Run DeepSearch with DeepSeek-R1 model

We can specify to search up to 30 results and limit the search to the last 360 days.

```bash
leet flow -e .env.fireworks -t digest -k aijob.fireworks \
    -p search_max_results=30 -p days_limit=360 \
    -q "How will agentic AI and generative AI affect our non-tech jobs?"  \
    -l info -o outputs/aijob.fireworks.md
```

The example output is in [examples/deepseek/aijob.fireworks.md](examples/deepseek/aijob.fireworks.md).

The output from

- OpenAI o1-pro model: https://chatgpt.com/share/67a6a4db-1564-800f-baae-a6b127366947
- Google Gemini 1.5-pro model: https://g.co/gemini/share/d63f48b93981
