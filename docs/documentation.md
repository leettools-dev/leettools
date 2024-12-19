
# LeetTools

## Key Componets

LeetTools provides the following key components:

- A document pipelines to ingest, convert, chunkm, embed, and index documents. User 
  specifies a document source such as a searfch query, a local directory, or a single 
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
- A search and retrieval libaray used by the document pipeline to retrieve documents. 
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
  schedule the tasks using more sophisicated schedulers, but we provide an integrated
  simple scheduler to avoid complex setup and unecessary dependencies for basic workloads.
- An accounting system to track the usage of the LLM APIs. For all LLM API calls used in
  the pipeline and workflow, the system records the prompts, the provider, the tokens
  used, the results to returned. The goal is to provide observability to the whole
  pipeline and foundation for optimization.

All you need to do to implement a search-based AI tool is to write a signal Python script
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

You can generate an article with a specific style from the search results. For example,
you can generate a news article with a specific style:

- Specify the number of days to search for news (right now only Google search is 
  supported for this option);
- LeetTools crawls the web with the keywords in the topic and scrape the top documents to
  the knowledge base;
- Saved documents are processed through the document pipeline: conversion, chunking, and
  indexing;
- The summaries for the documents are provided to the LLM API to generate a news article
  with the specified style;
- You can specify the output language, the number of words, and article style.


## Local command line commands

Then you can run the command line commands, assuming all commands are run under the root
directory of the project. Run the "eds list" command to see all the available commands:

```bash
% eds list
list	List all CLI commands and subcommands.
...
flow	Run the flow for the query.
```

### flow execution

You can run any flow using the `eds flow` command.

```bash
# list all the flows
eds flow --list
# check the parameters for a flow
eds flow -t answer --info
# run an answer flow with the default settings
eds flow -t answer -q "What is GraphRAG"
# run an answer flow with extra parameters
eds flow -t answer -q "What is GraphRAG" -p days_limit=3 -p output_language=fr
# run an answer flow and save the output to a KB
eds flow -t answer -q "What is GraphRAG" -k graphrag_kb
# run an anwser flow on the local KB
eds flow -t answer -q "What is GraphRAG" -k graphrag_kb -p retriever_type=local
```

### Add a local directory to the KB

For example, to add a directory to the default KB:

```bash
# you need to specify the ingestion_dir and the doc_source
# export ingestion_dir=<your_dir>
# export doc_source=<name_of_doc_source>
# you can also specify a -k option to specify the KB name
eds kb add-local-dir -p ${ingestion_dir} -s ${doc_source} -k ${kb_name}
```
