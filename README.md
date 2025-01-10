<p align="center">
  <img src="docs/assets/LTC-Logo-leettools-normal.png" alt="Logo" width="200"/>
</p>


[![Follow on X](https://img.shields.io/twitter/follow/LeetTools?logo=X&color=%20%23f5f5f5)](https://twitter.com/intent/follow?screen_name=LeetTools)
[![GitHub license](https://img.shields.io/badge/License-Apache_2.0-blue.svg?labelColor=%20%23155EEF&color=%20%23528bff)](https://github.com/leettools-dev/leettools)

- [AI Search Assistant with Local Knowledge Base](#ai-search-assistant-with-local-knowledge-base)
- [Quick start](#quick-start)
- [Use Different LLM Endpoints](#use-different-llm-endpoints)
- [Main Components](#main-components)
- [Community](#community)


# AI Search Assistant with Local Knowledge Base

LeetTools is an AI search assistant that can perform highly customizable search workflows
and save the search results and generated outputs to local knowledge bases. With an
automated document pipeline that handles data ingestion, indexing, and storage, we can
easily run complext search workflows that query, extract and generate content from the
web or local knowledge bases. 

LeetTools can run with minimal resource requirements on the command line with a 
DuckDB-backend and configurable LLM settings. It can be easily integrated with other 
applications need AI search and knowledge base support.

Here is a demo of LeetTools in action to answer the question "How does GraphRAG work?":

![LeetTools Overview](https://gist.githubusercontent.com/pengfeng/30b66efa58692fa3bc94af89e0895df4/raw/7a274cd60fbe9a3aabad56e5fa1a9c7e7021ba21/leettools-answer-demo.svg)

Currently LeetTools provides the following workflow:

* answer  : Answer the query directly with source references (similar to Perplexity). [📖](docs/flow-answer.md)
* digest  : Generate a multi-section digest article from search results (similar to Google Deep Research). [📖](docs/flow-digest.md)
* search  : Search for top segements that match the query. [📖](docs/flow-search.md)
* news    : Generate a list of news items for the specified topic. [📖](docs/flow-news.md)
* extract : Extract and store structured data for given schema. [📖](docs/flow-extract.md)
* opinions: Generate sentiment analysis and facts from the search results.  [📖](docs/flow-opinions.md)

# Quick start

```bash
% git clone https://github.com/leettools-dev/leettools.git
% cd leettools

% conda create -y -n leettools python=3.11
% conda activate leettools
% pip install -r requirements.txt
% pip install -e .

# where we store all the data and logs
% export LEET_HOME=${HOME}/leettools
% mkdir -p ${LEET_HOME}

# add the script path to the path
% export PATH=`pwd`/scripts:${PATH}

# set the OPENAI_API_KEY or put it in the .env file
# or any OpenAI-compatible LLM inference endpoint
# export EDS_DEFAULT_OPENAI_BASE_URL=https://api.openai.com/v1
% export EDS_OPENAI_API_KEY=<your_openai_api_key>
# or
% echo "EDS_OPENAI_API_KEY=<your_openai_api_key>" >> `pwd`/.env

# now you can run the command line commands
# flow: the subcommand to run different flows, use --list to see all the available flows
# -t run this 'answer' flow, use --info option to see the function description
# -q the query
# -k save the scraped web page to the knowledge base
# -l log level, info shows the essential log messages
% leet flow -t answer -q "How does GraphRAG work?" -k graphrag -l info
```

We can use any OpenAI-compatible LLM inference endpoint by setting the related 
environment variable. An example of using the DeepSeek API is described [here](docs/deepseek.md).

Here is an example output of the `answer` flow:

```markdown
** Sample Output **
# How Does Graphrag Work?
GraphRAG operates by constructing a knowledge graph from a set of documents, which
involves several key steps. Initially, it ingests textual data and utilizes a large
language model (LLM) to extract entities (such as people, places, and concepts) and
their relationships, mapping these as nodes and edges in a graph structure[1]. 

The process begins with pre-processing and indexing, where the text is segmented into
manageable units, and entities and relationships are identified. These entities are
then organized into hierarchical "communities," which are clusters of related topics
that allow for a more structured understanding of the data[2][3]. 

When a query is made, GraphRAG employs two types of searches: Global Search, which
looks across the entire knowledge graph for broad connections, and Local Search, which
focuses on specific subgraphs for detailed information[3]. This dual approach enables
GraphRAG to provide comprehensive answers that consider both high-level themes and
specific details, allowing it to handle complex queries effectively[3][4].

In summary, GraphRAG enhances traditional retrieval-augmented generation (RAG) by
leveraging a structured knowledge graph, enabling it to provide nuanced responses that
reflect the interconnected nature of the information it processes[1][2].
## References
[1] [https://www.falkordb.com/blog/what-is-graphrag/](https://www.falkordb.com/blog/what-is-graphrag/)
[2] [https://medium.com/@zilliz_learn/graphrag-explained-enhancing-rag-with-knowledge-graphs-3312065f99e1](https://medium.com/@zilliz_learn/graphrag-explained-enhancing-rag-with-knowledge-graphs-3312065f99e1)
[3] [https://medium.com/data-science-in-your-pocket/how-graphrag-works-8d89503b480d](https://medium.com/data-science-in-your-pocket/how-graphrag-works-8d89503b480d)
[4] [https://github.com/microsoft/graphrag/discussions/511](https://github.com/microsoft/graphrag/discussions/511)
```

# Use Different LLM Endpoints

We can run LeetTools with different env files to use different LLM endpoints and other
related settings. For example, if you have a local Ollama serving instance, you can set
to use it as follows:

```bash
% cat > .env.ollama <<EOF
# need tot change LEET_HOME to the correct path
LEET_HOME=/Users/myhome/leettools
EDS_DEFAULT_OPENAI_BASE_URL=http://localhost:11434/v1
EDS_OPENAI_API_KEY=dummy-key
EDS_DEFAULT_OPENAI_MODEL=llama3.2
# remove the following line if you have a separate embedder compatible with OpenAI API
# the following line specifies to use a local embedder
EDS_DEFAULT_DENSE_EMBEDDER=dense_embedder_local_mem
EOF

# Then run the command with the -e option to specify the .env file to use
% leet flow -e .env.ollama -t answer -q "How does GraphRAG work?" -k graphrag -l info
```

# Main Components

The main components of the backend include:
* 🚀 Automated document pipeline to ingest, convert, chunk, embed, and index documents.
* 🗂️ Knowledge base to manage and serve the indexed documents.
* 🔍 Search and retrieval library to fetch documents from the web or local KB.
* 🤖 Workflow engine to implement search-based AI workflows.
* ⚙ Configuration system to support dynamic configurations used for every component.
* 📝 Query history system to manage the history and the context of the queries.
* 💻 Scheduler for automatic execution of the pipeline tasks.
* 🧩 Accounting system to track the usage of the LLM APIs.

The architecture of the document pipeline is shown below:

![LeetTools Document Pipeline](https://gist.githubusercontent.com/pengfeng/4b2e36bda389e0a3c338b5c42b5d09c1/raw/6bc06db40dadf995212270d914b46281bf7edae9/leettools-eds-arch.svg)

See the [Documentation](docs/documentation.md) for more details.


# Community

**Acknowledgements**

Right now we are using the following open source libraries and tools (not limited to):

- [DuckDB](https://github.com/duckdb/duckdb)
- [Docling](https://github.com/DS4SD/docling)
- [Chonkie](https://github.com/bhavnicksm/chonkie)
- [Ollama](https://github.com/ollama/ollama)
- [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/)
- [BS4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

We plan to add more plugins for different components to support different workloads.

**Get help and support**

Please feel free to connect with us using the [discussion section](https://github.com/leettools-dev/leettools/discussions).


**Contributing**

Please read [Contributing to LeetTools](CONTRIBUTING.md) for details.

**License**

LeetTools is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) 
for the full license text.

