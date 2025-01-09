## Feature: Answer

The Answer workflow in LeetTools is designed to provide direct answers to user queries,
enriched with source references. It searches through local knowledge bases (KBs) or the
web, retrieving the most relevant information to answer the query effectively. With
configurable options, users can tailor the answer generation process to their specific
needs, including the style of the answer, language, and source filtering.

### How it Works:

1. Query Processing:

   The workflow initiates by receiving a query, which can either be targeted at a local
   knowledge base (KB) or the web (the entire web or specific targeted websites). If a
   local KB is specified, the system searches the relevant content; otherwise, it pulls
   the query results from the web via a search engine (e.g., Google).

2. Retriever Mechanism:

   - Local KB Search: If specified to use 'local' retriever, the query is performed on the
      local KB specified using "-k". If the `docsource_uuid` parameter is specified, we
      can limit the search to a specific document source such as an imported local dir.
   - Web Search: When specified to use a search engine as the retriever, the workflow
      performs a web search to fetch top documents by using the query as a keyword search.
      The search behavior can be further customized with parameters like `days_limit` and
      `target_site`.
   
3. Document Pipeline:

   If retriever is set to a search engine, the fetched search results are processed 
   through the document pipeline, which includes:

   - Conversion: Raw documents are transformed into markdown format.
   - Chunking: Markdown documents are split into smaller, manageable segments with their
      structural information.
   - Indexing: These segments are indexed for efficient retrieval and context formation.

4. Contextual Retrieval:

   Based on the user query, the workflow retrieves the most relevant segments from the KB.
   These segments are then concatenated to create a cohesive context, providing the LLM
   with detailed background information.

5. Answer Generation:

   Using the context formed from the retrieved segments, the LLM generates an answer to
   the query with references to the source. Some additional parameters enhance the answer
   customization:

   - Word Count (`word_count`): Control the length of the generated answer, or leave it
      empty for automatic word count adjustment.
   - Language (`output_language`): Specify the language in which the result should be output.
   - Reference Style (`reference_style`): Select the reference style, such as default or
    news, for the citations in the answer.
   - Strict Context (`strict_context`): Determine whether the LLM should strictly adhere
      to the context when generating the answer.
   
6. Search Customization:

   The web search process can be further customized with the following parameters:

   - Search Iteration (`search_iteration`): You can define how many additional pages
      the search should explore.
   - Search Max Results (`search_max_results`): Limit the number of search results 
      returned by the web retriever.
   - Target Site (`target_site`): Limit the search to a specific website if needed.
   - Days Limit (`days_limit`): Limit the search to a specified number of days, or leave
      it empty for no time restriction.

### Key Benefits:

- Customization: Customize your search and answer generation with options such as
   output style, word count, language, and reference format.
- Efficiency: Automate the search and answer generation process, reducing manual work.
- Contextual Accuracy: By leveraging contextual retrieval and LLM-based response
   generation, answers are both precise and comprehensive.
- Transparency: Source references are provided alongside the answers for verification
   and reliability.

### Example Use Case:

To search for an answer related to "Quantum Computing", you can specify:

- Article Style as "technical blog post"
- Word Count as 500 words
- Language as English
- Excluded Sites like "example.com"
- Target Site as "news.ycombinator.com"
- Knowledge Base as "quantum_kb" (created on demand if not exists)

Try this command in your terminal:

```bash
leet flow -t answer -q "What is Quantum Computing?" -k quantum_kb -l info \
   -p article_style="technical blog post" -p word_count=500 -p output_language="en" \
   -p excluded_sites="example.com" -p target_site="news.ycombinator.com" 
```

### Usage Info

You can get the detailed usage information for the Answer workflow by running the following command:

```bash
leet flow -t answer --info
====================================================================================================
answer: Answer the query directly with source references.

Search the web or local KB with the query and answer with source references:
- Perform the search with retriever: "local" for local KB, a search engine
  (e.g., google) fetches top documents from the web. If no KB is specified, 
  create an adhoc KB; otherwise, save and process results in the KB.
- New web search results are processed by the document pipeline: conversion,
  chunking, and indexing.
- Retrieve top matching segments from the KB based on the query.
- Concatenate the segments to create context for the query.
- Use the context to answer with source references via an LLM API call.

====================================================================================================
Use -p name=value to specify options for answer:

article_style       : The style of the output article such as analytical research reports, humorous
                      news articles, or technical blog posts. [default: analytical research reports]
                      [STEP: inference]
days_limit          : Number of days to limit the search results. 0 or empty means no limit. In
                      local KB, filters by the import time.
                      [STEP: search_to_docsource, web_searcher]
docsource_uuid      : The docsource uuid to run the query on when querying local KB.
                      [STEP: vector_search]
excluded_sites      : List of sites separated by comma to ignore when search for the information.
                      Empty means no filter. [STEP: web_searcher]
image_search        : When searching on the web, limit the search to image search.  [default: False]
                      [STEP: web_searcher]
output_example      : The example of the expected output content. If left empty, no example will be
                      provided to LLM. [STEP: inference]
output_language     : Output the result in the language. [STEP: inference]
reference_style     : The style of the references in the output article. Right now only default and
                      news are supported. [default: default] [FLOW: answer, answer]
retriever_type      : The type of retriever to use for the web search. [default: google]
                      [STEP: search_to_docsource, web_searcher] [FLOW: answer]
search_iteration    : If the max result is not reached, how many times we go to the next page.
                      [default: 3] [STEP: web_searcher]
search_max_results  : The maximum number of search results for retrievers to return. Each retriever
                      may have different paging mechanisms. Use the parameter and the search
                      iteration to control the number of results. [default: 10]
                      [STEP: search_to_docsource, web_searcher]
strict_context      : When generating a section, whether to use strict context or not.
                      [default: False] [STEP: inference]
target_site         : When searching the web, limit the search to this site. Empty means search all
                      sites. [STEP: web_searcher]
word_count          : The number of words in the output section. Empty means automatics.
                      [STEP: inference]
```

