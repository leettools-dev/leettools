<p align="center">
    <!-- placeholder for banner -->
</p>

[![Follow on X](https://img.shields.io/twitter/follow/LeetTools?logo=X&color=%20%23f5f5f5)](https://twitter.com/intent/follow?screen_name=LeetTools)
[![GitHub license](https://img.shields.io/badge/License-Apache_2.0-blue.svg?labelColor=%20%23155EEF&color=%20%23528bff)](https://github.com/leettools-dev/leettools)

# LeetTools

Open Source AI Search Tools

---

## Problems

LLM-based search applications such as Perplexity and ChatGPT search have become 
increasingly popular recently. However, instead of simple question-answering interactions, 
sometimes we need perform more complex search-based tasks that need iterative workflows, 
personalized data curation, and domain-specific knowledge integration. 

Here are a few examples:
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

See the [Documentation](docs/documentation.md) for more design details.


## Get help and support

Please feel free to connect with us using the [discussion section](https://github.com/leettools-dev/leettools/discussions).


## Contributing

Please read [Contributing to LeetTools](https://github.com/leettools-dev/leettools/blob/main/CONTRIBUTING.md) for details.

## License

LeetTools is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) 
for the full license text.

