[![Follow on X](https://img.shields.io/twitter/follow/LeetTools?logo=X&color=%20%23f5f5f5)](https://twitter.com/intent/follow?screen_name=LeetTools)
[![GitHub license](https://img.shields.io/badge/License-Apache_2.0-blue.svg?labelColor=%20%23155EEF&color=%20%23528bff)](https://github.com/leettools-dev/leettools)

# LeetTools

## Open Source AI Search Tools

LeetTools allows you to run highly customizable search workflows to query, extract, and 
generate information from the web or local knowledge bases. Instead of using a web
page to interact with the search engine, we can run complex search workflows or automated
search tasks from the command line.

For example, when we search for a topic, we can go through the top X pages of the search
results instead of only the first one, filter out the unrelated ones, and then generate
a digest article from the relevant search results with citation to the source. This 
process works very similar to other AI search engines such as Perplexity and ChatGPT
Search, but with LeetTools, you can customize the search workflow to fit your needs. 
For example, you can easily

1. ask the question in language X, search in language Y, and summarize in language Z.
2. only search in a specific domain, or exclude certain domains from the search.
3. only search for recent documents from the last X days.
4. control the output: style, number of words, and number of sections, etc.
5. extract structured information instead of generating answers.

The relevant documents scraped during the search are stored in a local knowledge base
and you can query it again for related questions. You can add your own documents to the
knowledge base and use them in the search workflow. The system is designed to 
be modular and extensible; all the components are implemented as plugins allowing to use
different components and configurations.

LeetTools provides an easy way to implement search-related function in daily workflows.
For this version, all the data operations are backed by the in-memory database DuckDB to
reduce the resource footprints. You can easily run it on the command line or a cron
job to automate the search tasks. 

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
% export EDS_OPENAI_API_KEY=your_openai_api_key
# or
% echo "EDS_OPENAI_API_KEY=your_openai_api_key" > `pwd`/.env

# now you can run the command line commands
# flow: the subcommand to run different flows, use --list to see all the available flows
# -t run this 'answer' flow, use --info option to see the function description
# -q the query
# -k save the scraped web page to the knowledge base
# -l log level, info shows the essential log messages
% leet flow -t answer -q "How does GraphRAG work?" -k graphrag -l info
```

```markdown
** Sample Output **
# What Is GraphRAG
GraphRAG is an advanced approach to Retrieval-Augmented Generation (RAG) that integrates knowledge graphs with large language models (LLMs) to enhance the generation of responses based on retrieved information. Its primary purpose is to improve the accuracy and relevance of generated outputs by leveraging the structured relationships within knowledge graphs, which allows for a more comprehensive contextual understanding of the data being processed[[1](#reference-1)][[2](#reference-2)].

One of the key enhancements GraphRAG brings to traditional RAG techniques is its ability to connect disparate pieces of information through their shared attributes, enabling the model to synthesize new insights. This is particularly beneficial for complex queries that require multi-hop reasoning or the integration of information from various sources[[3](#reference-3)][[4](#reference-4)]. By utilizing knowledge graphs, GraphRAG can better understand the relationships and dependencies between different pieces of information, leading to more coherent and contextually appropriate responses[[5](#reference-5)][[6](#reference-6)].

The benefits of GraphRAG compared to traditional RAG techniques include:

1. **Enhanced Knowledge Representation**: GraphRAG captures complex relationships between entities and concepts, allowing for a richer understanding of the data[[7](#reference-7)][[8](#reference-8)].
2. **Explainability**: The use of knowledge graphs makes the decision-making process of the AI more transparent, enabling users to trace errors and understand the reasoning behind outputs[[9](#reference-9)][[10](#reference-10)].
3. **Improved Contextual Understanding**: By grounding responses in factual knowledge, GraphRAG reduces the risk of generating incorrect or misleading information, a common issue in traditional RAG systems[[11](#reference-11)][[12](#reference-12)].
4. **Scalability and Efficiency**: GraphRAG can handle large datasets more efficiently, as it is built on fast knowledge graph stores, which can optimize performance and reduce costs associated with vector databases[[13](#reference-13)][[14](#reference-14)].

Overall, GraphRAG represents a significant advancement in the field of AI, particularly in applications requiring high precision and the ability to reason over complex relationships within data[[15](#reference-15)][[16](#reference-16)].
## References
[1] [https://medium.com/@amrwrites/you-probably-dont-need-graphrag-0bc9cf671db1](https://medium.com/@amrwrites/you-probably-dont-need-graphrag-0bc9cf671db1)

[2] [https://medium.com/@zilliz_learn/graphrag-explained-enhancing-rag-with-knowledge-graphs-3312065f99e1](https://medium.com/@zilliz_learn/graphrag-explained-enhancing-rag-with-knowledge-graphs-3312065f99e1)

[3] [https://www.datastax.com/guides/graph-rag](https://www.datastax.com/guides/graph-rag)

[4] [https://www.falkordb.com/blog/what-is-graphrag/](https://www.falkordb.com/blog/what-is-graphrag/)

[5] [https://www.ontotext.com/knowledgehub/fundamentals/what-is-graph-rag/](https://www.ontotext.com/knowledgehub/fundamentals/what-is-graph-rag/)

[6] [https://microsoft.github.io/graphrag/](https://microsoft.github.io/graphrag/)
```

Right now LeetTools provides the following flows:

* answer  : Answer the query directly with source references.
* digest  : Generate a multi-section digest article from search results.
* search  : Search for top segements that match the query.
* news    : Generate a news-style article from the search results.
* extract : Extract information from the search results and output as csv.


See the [Documentation](docs/documentation.md) for more details.


## Libraries and APIs used

Right now the default settings are using the following libraries and APIs:

- [Google Search API](https://developers.google.com/custom-search/v1/overview)
- [OpenAI API](https://beta.openai.com/docs/api-reference/completions/create)
- [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/)
- [BS4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [DuckDB](https://github.com/duckdb/duckdb)
- [Docling](https://github.com/DS4SD/docling)
- [Chonkie](https://github.com/bhavnicksm/chonkie)

We plan to add more plugins for different components to support different workloads.

## Get help and support

Please feel free to connect with us using the [discussion section](https://github.com/leettools-dev/leettools/discussions).


## Contributing

Please read [Contributing to LeetTools](CONTRIBUTING.md) for details.

## License

LeetTools is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) 
for the full license text.

