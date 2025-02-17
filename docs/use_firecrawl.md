# Use FireCrawl as Search Engine and Web Crawler

1. Get an API key from [FireCrawl](https://www.firecrawl.dev/).
2. Add the API key to your environment variables:
```bash
export EDS_FIRECRAWL_API_KEY=your_api_key
```
or add the api key to the your .env file:
```bash
echo "EDS_FIRECRAWL_API_KEY=your_api_key" >> .env
```
3. Use the firecrawl search engine:
```bash
leet flow -t answer -p retriever_type=firecrawl -l info \
    -q "How does GraphRAG work?" -k graphrag 
```
4. We can also use the firecrawl scraper as the backup scraper if the default scraper fails:
```bash
export EDS_FALLBACK_SCRAPER="firecrawl"
```
Currently the default scraper is `beautiful_soup`.
5. To use the firecrawl scraper as the default scraper, set the `EDS_DEFAULT_SCRAPER` 
environment variable to `firecrawl` (note that the default beautiful_soup scraper is free):
```bash
export EDS_DEFAULT_SCRAPER="firecrawl"
```

Note that you can run the FireCrawl search engine locally:
https://github.com/mendableai/firecrawl/blob/main/CONTRIBUTING.md

# Use FireCrawl and Ollama to run Deep Research

First we need to create a customized LLAMA3.2 model with a bigger context window. The
default of Ollma is 2K and not enough for the summary tasks.

```bash
cat > llama3.2_8k <<EOF
FROM llama3.2:latest
PARAMETER num_ctx 8096
EOF

ollama create llama3.2_8k -f llama3.2_8k
```

Then we create a new environment file for the FireCrawl search engine and local Ollama:

```bash
cat > .env.ollama.firecrawl <<EOF
EDS_DEFAULT_LLM_BASE_URL=http://localhost:11434/v1
EDS_LLM_API_KEY=dummy-key
EDS_DEFAULT_INFERENCE_MODEL=llama:3.2_8k
EDS_DEFAULT_EMBEDDING_MODEL=nomic-embed-text
EDS_EMBEDDING_MODEL_DIMENSION=768

EDS_WEB_RETRIEVER=firecrawl
EDS_FIRECRAWL_API_KEY=your_api_key

# Optional
# modify the URL if you run FireCrawl locally
# EDS_FIRECRAWL_API_URL=https://api.firecrawl.dev
# use firecrawl as the default scraper, system default is beautiful_soup
# EDS_DEFAULT_SCRAPER=firecrawl
# we can use beautiful_soup as the main scraper and firecrawl as the backup scraper
# EDS_FALLBACK_SCRAPER=firecrawl
EOF
```

Now you can run digest flow with the FireCrawl search engine and Ollama:

```bash
% leet flow -e .env.ollama.firecrawl -t digest -k aijob.ollama \
    -q "How will agentic AI and generative AI affect our non-tech jobs?"  \
    -l debug -o aijob.ollama.firecrawl.md
```
