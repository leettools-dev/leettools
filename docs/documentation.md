# LeetTools

## Problems

LLM-based search applications such as Perplexity and ChatGPT search have become 
increasingly popular recently. However, instead of simple question-answering interactions, 
sometimes we need to perform more complex search-based tasks that need iterative workflows,
personalized data curation, and domain-specific knowledge integration. 

```Markdown title="Example: Search and Summarize"
When we do a web search, since the content we need may not always be available on the 
first page of search results, can we go a few more pages to find only relevant documents
and then summarize the relevant information? For such a search workflow, we can:
1. Use a search engine to fetch the top documents, up to X pages.
2. Crawl the result URLs to fetch the content.
3. Use LLM to summarize the content of each page to see if the content is relevant.
4. We can also crawl links found in the content to fetch more relevant information.
5. When we reach a predefined threshold, say number of relevant documents, or number of
   iterations, we can stop the search.
6. Aggregate all the relevant summaries to generate a list of topics discussed in the
   search results.
7. Use the topics to generate a digest article that summarizes the search results.
```

Here are a few more examples:
- Simple:
    - Search and summarize: search for a topic, in the search results, go through the top
        X instead of only the top 10, filter out the unrelated ones, generate a digest 
        article from the search results.
    - Customized search: Can I limit my search to a specific domain or source or a date range? 
        Can I query in language X, search in language Y, and generate the answer in language Z?
        Can I exclude the search results from a specific source? Can I generate the results
        in a specific style with a specific length?
- Complex:
    - Extract and dedupe: find all entities that satisfy a condition, extract required
        information as structured data, and deduplicate the results.
    - Search and aggregate: given a product, search for all recently reviews and feedbacks,
        identify the sentiment, the product aspects, and the suggestions, aggregate the
        results based on the sentiment and the aspects.
- Hard:
    - Dynamic streaming queries: monitor the web for a specific topic, find the "new" and "hot"
        information that I have not seen before and satisfies a certain criteria, summarize
        or extract the content I need and generate a report in my customized format.

After analyzing why it is hard to implement such tasks, we found that the main reason
is the lack of data support for the iterative workflows. Therefore, we want to make 
a persistent data layer to support the complex logic required for such tasks.


## Solution: search flow with a document pipeline
LeetTools enables implementation of automated search flows backed by a local document
pipeline. Besides the common benefits of a private deployment such as security and using
local models, LeetTools provides many benefits:

- integrated pipeline to abstract away the complex setup for all the components;
- easier to implement customized/automated/complex search-task logic;
- better control over the indexing, retrieval, and ranking process;
- allow personalized data curations and annotations process;
- more flexible to adapt models and functionalities suitable for the requirements.


## Key Components

![LeetTools Document Pipeline](https://gist.githubusercontent.com/pengfeng/4b2e36bda389e0a3c338b5c42b5d09c1/raw/6bc06db40dadf995212270d914b46281bf7edae9/leettools-eds-arch.svg)

LeetTools provides the following key components:

- A document pipeline to ingest, convert, chunk, embed, and index documents. User 
  specifies a document source such as a search query, a local directory, or a single 
  file, the pipeline will ingest the documents specified by the source to a document 
  sink (the original form of the document) and convert the original document into the
  standard Markdown format document. The Markdown document is then split and indexed 
  using different configurable strategies. The pipeline is similar to the ETL process
  of the data pipeline, but the target is now documents instead of structured or 
  semi-structured data.
- A knowledge base to manage and serve the indexed documents, including the documents, 
  the segments, the embeddings, the document graph, the entity graph, which can be 
  supported by different storage plugins. In this version, we provide the DuckDB-based
  implementations to minimize the resource footprint.
- A search and retrieval library used by the document pipeline to retrieve documents. 
  We can use search APIs such as Google, Bing, and Tavily, and scraper APIs such as 
  Firecrawl or Crawl4AI. 
- A workflow engine to implement search-based AI workflows, which provides a thin-layer
  of abstraction to manage the dependencies and configurations.
- A configuration system to manage the configurations used in the pipeline, such as the
  different endpoints, different parameters in the retrieval process, and etc.
- A query history system to manage the history and the context of the queries.
- A scheduler to schedule the execution of the ingestions. We provide a simple pull-based
  scheduler that queries the knowledgebase and execute different tasks (ingestion,
  converting, splitting, indexing) based on the status of the documents. It is possible to
  schedule the tasks using more sophisticated schedulers, but we provide an integrated
  simple scheduler to avoid complex setup and unnecessary dependencies for basic workloads.
- An accounting system to track the usage of the LLM APIs. For all LLM API calls used in
  the pipeline and workflow, the system records the prompts, the provider, the tokens
  used, the results returned. The goal is to provide observability to the whole
  pipeline and foundation for optimization.

All you need to do to implement a search-based AI tool is to write a single Python script
that organizes different components in the LeetTools framework. An example of such a
script is shown in 
[src/leettools/flow/flows/answer/flow_answer.py](src/leettools/flow/flows/answer/flow_answer.py), 
which implements the search-extract-answer flow similar to the existing AI search services.

So, if you want to implement personalized search-based workflows that can accumulate
domain-specific knowledge with a persistent local memory, but setting up all the 
components from scratch is too much work, LeetTools is the right tool for you.

## Demo Cases

We list a few demo use cases that are provided in the codebase:

### Answer with references (similar to Perplexity AI)

Search the web or local KB with the query and answer with source references:

- Perform the search with retriever: "local" for local KB, a search engine
  (e.g., google) fetches top documents from the web. If no KB is specified, 
  create an adhoc KB; otherwise, save and process results in the KB.
- New web search results are processed by the document pipeline: conversion,
  chunking, and indexing.
- Retrieve top matching segments from the KB based on the query.
- Concatenate the segments to create context for the query.
- Use the context to answer with source references via an LLM API call.

### Search and Summarize

When interested in a topic, you can generate a digest article from the search results:

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

### Search and Extract

Extra structured data from web or local KB search results:
- Perform the search with retriever: "local" for local KB, a search engine (e.g., Google)
  fetches top documents from the web. If no KB is specified, create an adhoc KB; 
  otherwise, save and process results in the KB.
- New web search results are processed through the document pipeline: conversion, 
  chunking, and indexing.
- Extract structured data from matched documents based on the specified model.
- Display the extracted data as a table in the output.


### Search and generate with style

You can generate an article with a specific style from the search results. 

- Specify the number of days to search for news (right now only Google search is 
  supported for this option);
- LeetTools crawls the web with the keywords in the topic and scrape the top documents to
  the knowledge base;
- Saved documents are processed through the document pipeline: conversion, chunking, and
  indexing;
- The summaries for the documents are provided to the LLM API to generate a news article
  with the specified style;
- You can specify the output language, the number of words, and article style.


## Command line commands

Then you can run the command line commands, assuming all commands are run under the root
directory of the project. Run the "leet list" command to see all the available commands:

```bash
% leet list
list	List all CLI commands and subcommands.
...
flow	Run the flow for the query.
```

### flow execution

You can run any flow using the `leet flow` command.

```bash
# list all the flows
leet flow --list
# check the parameters for a flow
leet flow -t answer --info
# run an answer flow with the default settings
leet flow -t answer -q "What is GraphRAG"
# run an answer flow with extra parameters, such as the days_limit and output_language
leet flow -t answer -q "What is GraphRAG" -p days_limit=3 -p output_language=es
# run an answer flow and save the output to a KB
leet flow -t answer -q "What is GraphRAG" -k graphrag
# run an answer flow on the local KB
leet flow -t answer -q "What is GraphRAG" -k graphrag -p retriever_type=local
# run an digest of search results from the last three days and output in Spanish
# this query will run for a while to fetch and analyze the search results
leet flow -t digest -q "LLM GenAI News" -k genai -p days_limit=3 -p output_language=es -l info
# extract the structured data from the search results
leet flow -t extract -q "LLM GenAI Startup" -k genai -p extract_pydantic=docs/company.py -l info
```