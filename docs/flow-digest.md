## **Feature: Digest**

The **Digest** workflow in LeetTools is designed to generate a comprehensive, 
multi-section digest article based on search results. Whether you're researching a 
topic or compiling relevant information, this feature helps you gather, summarize, 
and organize content into an easy-to-read digest, all with customizable options to
suit your specific needs.

### How it Works:

1. Query and Content Filtering:

   The user initiates the workflow by defining a search query. Optionally, the user can
   provide content instructions (`content_instruction`) to assess the relevance of the
   result documents. This helps refine the selection of content to be included in the
   digest article.

2. Retriever Mechanism:

   - Local KB Search: If `retriever_type` parameter is set to `local`, the query will
      be performed on the local knowledge base. If a docsource is specified using the
      `docsource_uuid` parameter, the query is limited to that docsource directly.
   - Web Search: If `retriever_type` parameter is not set or set to a search engine,
      the workflow searches the web using the search engine. Customizations like 
      `excluded_sites` (to filter out specific domains) or `target_site` (to restrict 
      searches to a specific website) can be applied.

3. Document Pipeline:

   If retriever is set to a search engine, the fetched search results are processed 
   through the document pipeline, which includes:

   - Conversion: Raw documents are transformed into markdown format.
   - Chunking: Markdown documents are split into smaller, manageable segments with their
      structural information.
   - Indexing: These segments are indexed for efficient retrieval and context formation.

4. Summarization and Topic Planning:

   Each document in the search results is summarized using an LLM API call. A topic plan
   for the digest article is then generated based on these summaries. The user can 
   specify the number of sections (`num_of_sections`) for the article or let the planning
   agent decide automatically.

5. Section Creation:

   The digest article is divided into sections based on the topic plan. Content from the
   KB or the web is used to fill in each section. The sections are then concatenated into
   a cohesive article.

6. Customization Options:

   Users can customize the output using the following parameters:

   - Article Style (`article_style`): Choose from various output styles, such as 
      analytical research reports, humorous news articles, or technical blog posts.
   - Output Language (`output_language`): Output the result in a specific language.
   - Word Count (`word_count`): Specify the desired word count for each section.
   - Recursive Scraping (`recursive_scrape`): Enable recursive scraping to gather 
      additional content from URLs found in the search results.
   - Search Customization: Control search behavior with options like `search_max_results`,
      `search_iteration`, and `scrape_max_count`.

1. Final Article Generation:

   After generating and organizing the sections, the digest article is composed and
   returned in the specified format, complete with references and citations based on the
   chosen `reference_style`.

### Key Benefits:

- Organized Content: Automatically generates a well-structured, multi-section digest
   article, perfect for research or content curation.
- Customization: Fine-tune the article style, word count, search behavior, and more to
   suit your specific needs.
- Efficient Research: Combine relevant information from various sources into a cohesive
   article with minimal manual effort.
- Transparency: Include references in the output with customizable citation styles,
   ensuring the credibility of the content.

### Example User Case:

To generate a digest article on "Quantum Computing," you can run the following command:

```bash
leet flow -t digest -q "What is Quantum Computing?" -k quantum_kb -l info \
   -p article_style="analytical research reports" \
   -p num_of_sections=5 -p output_language="en" \
   -p recursive_scrape=True -p search_max_results=15 -p search_iteration=2
```

### Usage Info

You can get the detailed usage information for the Digest workflow by running the 
following command:

```bash
leet flow -t digest --info
====================================================================================================
digest: Generate a multi-section digest article from search results.

When interested in a topic, you can generate a digest article:
- Define search keywords and optional content instructions for relevance filtering.
- Perform the search with retriever: "local" for local KB, a search engine (e.g., Google)
  fetches top documents from the web. If no KB is specified, create an adhoc KB; 
  otherwise, save and process results in the KB.
- New web search results are processed through the document pipeline: conversion, 
  chunking, and indexing.
- Each result document is summarized using a LLM API call.
- Generate a topic plan for the digest from the document summaries.
- Create sections for each topic in the plan using content from the KB.
- Concatenate sections into a complete digest article.

====================================================================================================
Use -p name=value to specify options for digest:

article_style       : The style of the output article such as analytical research reports, humorous
                      news articles, or technical blog posts. [default: analytical research reports]
                      [STEP: plan_topic, gen_intro, gen_section]
content_instruction : The relevance of the result documents from keyword search is assessed by the
                      content instruction if provided.  [STEP: plan_topic]
days_limit          : Number of days to limit the search results. 0 or empty means no limit. In
                      local KB, filters by the import time.
                      [STEP: search_to_docsource, web_searcher, local_kb_search]
docsource_uuid      : The docsource uuid to run the query on when querying local KB.
                      [STEP: vector_search]
excluded_sites      : List of sites separated by comma to ignore when search for the information.
                      Empty means no filter. [STEP: web_searcher]
image_search        : When searching on the web, limit the search to image search.  [default: False]
                      [STEP: web_searcher]
num_of_sections     : The number of sections in the output article. If left empty, the planning
                      agent will decide automatically. [STEP: plan_topic]
output_example      : The example of the expected output content. If left empty, no example will be
                      provided to LLM. [STEP: gen_intro, gen_section]
output_language     : Output the result in the language. [STEP: gen_intro, gen_section]
planning_model      : The model used to do the article planning. [default: gpt-4o-mini]
                      [STEP: plan_topic, gen_section]
recursive_scrape    : If true, scrape the top urls found in the search results documents.
                      [default: False] [FLOW: digest]
reference_style     : The style of the references in the output article. Right now only default and
                      news are supported. [default: default] [SUBFLOW: gen_essay]
retriever_type      : The type of retriever to use for the web search. [default: google]
                      [STEP: search_to_docsource, web_searcher] [FLOW: digest]
scrape_iteration    : When we do recursive scraping, we will not stop until we reach the max number
                      of results or the number of iterations specified here. [default: False]
                      [FLOW: digest]
scrape_max_count    : When we do recursive scraping, we will not stop until we reach the number of
                      max iterations or the max number of results specified here. [default: False]
                      [FLOW: digest]
search_iteration    : If the max result is not reached, how many times we go to the next page.
                      [default: 3] [STEP: web_searcher]
search_language     : The language used for keyword search if the search API supports.
                      [STEP: gen_search_phrases]
search_max_results  : The maximum number of search results for retrievers to return. Each retriever
                      may have different paging mechanisms. Use the parameter and the search
                      iteration to control the number of results. [default: 10]
                      [STEP: search_to_docsource, web_searcher, local_kb_search]
search_rewrite      : Ask the LLM to generate search keywords from the search query. [FLOW: digest]
strict_context      : When generating a section, whether to use strict context or not.
                      [default: False] [STEP: gen_intro, gen_section]
target_site         : When searching the web, limit the search to this site. Empty means search all
                      sites. [STEP: web_searcher]
word_count          : The number of words in the output section. Empty means automatics.
                      [STEP: gen_intro, gen_section]
```