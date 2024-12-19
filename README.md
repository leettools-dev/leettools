[![Follow on X](https://img.shields.io/twitter/follow/LeetTools?logo=X&color=%20%23f5f5f5)](https://twitter.com/intent/follow?screen_name=LeetTools)
[![GitHub license](https://img.shields.io/badge/License-Apache_2.0-blue.svg?labelColor=%20%23155EEF&color=%20%23528bff)](https://github.com/leettools-dev/leettools)

# LeetTools

## Open Source AI Search Tools

LeetTools allow you to run highly customizable search workflows to find, extract, and 
generate information from the web or local knowledge bases. The system is designed to 
be modular and extensible, allowing you to use different components and configurations
easily.

For example, since the content we need may not always be available on the first page of
search results, can we go a few more pages to find only relevant documents and then
summary the relevant information? For such a search workflow, we can:
1. Use a search engine to fetch the top documents, up to X pages.
2. Crawl the result URLs to fetch the content.
3. Use LLM to summarize the content of each page to see if the content is relevant.
4. We can also crawl links found in the content to fetch more relevant information.
5. When we reach a predefind threshold, say number of relevant documents, or number of
   iterations, we can stop the search.
6. Aggregate all the relevant summaries to generate a list of topics discussed in the
   search results.
7. Use the topics to generate a digest article that summarizes the search results.

This flow is similar to a lot of adavanced AI deep research tools. But with LeetTools,
you can customize the search workflow to fit your needs. For example, you can easily

1. ask the question in language X, search in language Y, and summarize in language Z.
2. only search in a specific domain, or exclude certain domains from the search.
3. only search for recent documents from the last X days.
4. control the output: style, number of words, and number of sections, etc.

The relevant documents scraped during the search are stored in a local knowledge base
and you can query it again for related questions. You can add your own documents to the
knowledge base and use them in the search workflow.

## Features

* 🚀 Automated document pipeline to ingest, convert, chunk, embed, and index documents.
* 🗂️ Knowledge base to manage and serve the indexed documents.
* 🔍 Search and retrieval library to fetch documents from the web or local KB.
* 🤖 Workflow engine to implement search-based AI workflows.
* ⚙ Configuration system to support dynamic configurations used for every component.
* 📝 Query history system to manage the history and the context of the queries.
* 💻 Scheduler for automatic execution of the pipeline tasks.
* 🧩 Accounting system to track the usage of the LLM APIs.

## Quick start

```bash
% git clone https://github.com/leettools-dev/leettools.git
% cd leettools

% conda create -n leettools python=3.11
% conda activate leettools
% pip install -r requirements.txt
% pip install -e .

# where we store all the data and logs
% export LEET_HOME=${HOME}/leettools
% mkdir -p ${LEET_HOME}

# add the script path to the path
% export PATH=`pwd`/scripts:${PATH}

# set the OPENAI_API_KEY or put it in the .env file
% export EDS_OPENAI_API_KEY=your_openai_api_key
# or
% echo "EDS_OPENAI_API_KEY=your_openai_api_key" > `pwd`/.env

# now you can run the command line commands
# flow: the subcommand to run different flows, use --list to see all the available flows
# -t run this 'answer' flow, use --info option to see the function description
# -q the query
# -k save the scraped web page to the knowledge base
# -l log level, info shows the essential log messages
% leet flow -t answer -q "How does GraphRAG work?" -k GraphRAG -l info
```

Right now we provide the following flows:

* answer  : Answer the query directly with source references.
* digest  : Generate a multi-section digest article from search results.
* search  : Search for top segements that match the query.
* news    : Generating a news-style article from the search results.
* extract : Extract information from the search results and output as csv.


See the [Documentation](docs/documentation.md) for more design details.


## Get help and support

Please feel free to connect with us using the [discussion section](https://github.com/leettools-dev/leettools/discussions).


## Contributing

Please read [Contributing to LeetTools](CONTRIBUTING.md) for details.

## License

LeetTools is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) 
for the full license text.

