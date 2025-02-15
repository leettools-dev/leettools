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

