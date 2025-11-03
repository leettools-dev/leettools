
- [Class Name: `StepExtendContext`](#class-name-stepextendcontext)
- [Class Name: `StepExtractInfo`](#class-name-stepextractinfo)
- [Class Name: `StepGenIntro`](#class-name-stepgenintro)
- [Class Name: `StepGenSearchPhrases`](#class-name-stepgensearchphrases)
- [Class Name: `StepGenSection`](#class-name-stepgensection)
- [Class Name: `StepInference`](#class-name-stepinference)
- [Class Name: `StepIntention`](#class-name-stepintention)
- [Class Name: `StepLocalKBSearch`](#class-name-steplocalkbsearch)
- [Class Name: `StepPlanTopic`](#class-name-stepplantopic)
- [Class Name: `StepQueryRewrite`](#class-name-stepqueryrewrite)
- [Class Name: `StepRerank`](#class-name-steprerank)
- [Class Name: `StepScrapeUrlsToDocSource`](#class-name-stepscrapeurlstodocsource)
- [Class Name: `StepSearchMedium`](#class-name-stepsearchmedium)
- [Class Name: `StepSearchToDocsource`](#class-name-stepsearchtodocsource)
# Class Name: `StepExtendContext`
- **Component Name**: `"extend_context"`
- **Dependencies**: None
- **Direct Flow Option Items**: None

**Functionality**
- **Purpose**: To generate an extended context using reranked search results and accumulated source items.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `reranked_result`: List of reranked search result segments.
    - `accumulated_source_items`: Dictionary of accumulated source items.
    - `override_model_name`: Optional model name to override the default.
  - **Returns**: A tuple containing the extended context, context token count, and a dictionary of accumulated source items.
- **Process**:
  - Determines the inference model name based on the strategy or default settings.
  - Calculates the context limit and adjusts it for token usage.
  - Optionally enables neighboring context expansion and adds chat history to the context.
  - Constructs the extended context and calculates its token count.

# Class Name: `StepExtractInfo`
- **Component Name**: `"extract_info"`
- **Short Description**: Extracts information from the document.
- **Full Description**: The function returns a list of the model class. If the instruction specifies extracting only one object, the caller should take the first object from the list.

**Functionality**
- **Purpose**: To extract structured information from a document based on provided instructions.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `content`: The content to extract information from.
    - `extraction_instructions`: Instructions for extracting the information.
    - `model_class`: The model class to extract the information into.
    - `model_class_name`: The name of the model class.
    - `multiple_items`: Boolean indicating whether to extract multiple items.
    - `query_metadata`: Optional metadata for the query.
  - **Returns**: A list of extracted objects of the specified model class.
- **Process**:
  - Uses a prompt template to guide the extraction process.
  - Constructs a user prompt with the content and extraction instructions.
  - Calls an inference API to extract the information.
  - Validates and returns the extracted information as a list of model class instances.

# Class Name: `StepGenIntro`
- **Component Name**: `"gen_intro"`
- **Dependencies**: None
- **Direct Flow Option Items**: Uses supported template option items.

**Functionality**
- **Purpose**: To generate an introduction section based on the content, typically a summary of related documents.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `content`: The content to base the introduction on.
    - `query_metadata`: Optional metadata for the query.
  - **Returns**: An `ArticleSection` containing the introduction.
- **Process**:
  - Determines the output language and sets the title accordingly.
  - Constructs a user prompt using the content and query.
  - Calls an inference API to generate the introduction.
  - Returns the introduction as an `ArticleSection` object.

# Class Name: `StepGenSearchPhrases`
- **Component Name**: `"gen_search_phrases"`
- **Short Description**: Generates search phrases for the query.
- **Full Description**: Generates search phrases using the specified search language if set, otherwise uses the original language.

**Functionality**
- **Purpose**: To create web search phrases that will return the most relevant information about a query from a web search engine.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `query_metadata`: Optional metadata for the query.
  - **Returns**: A string containing the generated search phrases.
- **Process**:
  - Retrieves the query content from `exec_info`.
  - Determines the search language.
  - Constructs a user prompt using the query and language instructions.
  - Calls an inference API to generate the search phrases.
  - Returns the generated search phrases as a string.

# Class Name: `StepGenSection`
- **Component Name**: `"gen_section"`
- **Short Description**: Generates a section based on the plan.
- **Full Description**: Searches the local knowledge base for related information and generates the section following the instructions in the plan and the options set in the query, such as style, words, language, etc.

**Functionality**
- **Purpose**: To generate a section of an article using a predefined plan and extended context.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `section_plan`: The plan for the section.
    - `query_metadata`: Metadata for the query.
    - `extended_context`: The extended context for the section.
    - `rewritten_query`: The rewritten query.
    - `previous_sections`: List of existing sections.
  - **Returns**: An `ArticleSection` containing the generated content.
- **Process**:
  - Retrieves the output language and flow options.
  - Constructs system and user prompts using the section plan and context.
  - Calls an inference API to generate the section content.
  - Returns the generated section as an `ArticleSection` object.

# Class Name: `StepInference`
- **Component Name**: `"inference"`
- **Dependencies**: None
- **Direct Flow Option Items**: Uses supported template option items.

**Functionality**
- **Purpose**: To execute an inference API call using a rewritten query and extended context.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `query_metadata`: Metadata for the query.
    - `rewritten_query`: The rewritten query.
    - `extended_context`: The extended context for the query.
  - **Returns**: A `ChatCompletion` object containing the result of the inference.
- **Process**:
  - Retrieves the inference strategy section from the execution information.
  - Uses the strategy to determine the inference method.
  - Constructs template variables for the inference call.
  - Executes the inference and returns the chat completion result.

# Class Name: `StepIntention`
- **Component Name**: `"intention"`
- **Dependencies**: None
- **Direct Flow Option Items**: None

**Functionality**
- **Purpose**: To determine the intention behind a query using a specified strategy.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
  - **Returns**: A `ChatQueryMetadata` object containing the intention of the query.
- **Process**:
  - Retrieves the intention strategy section from the execution information.
  - If no strategy is provided or if it is disabled, it uses the default intention.
  - Uses the strategy to determine the intention of the query.
  - Returns the intention as part of the `ChatQueryMetadata`.

# Class Name: `StepLocalKBSearch`
- **Component Name**: `"local_kb_search"`
- **Dependencies**: None
- **Direct Flow Option Items**: Includes options for days limit and maximum search results.

**Functionality**
- **Purpose**: To search the local knowledge base and retrieve the top documents related to a query.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `query`: Optional query string to search. If not provided, it uses the query from `exec_info`.
  - **Returns**: A list of `SearchResult` objects containing the search results.
- **Process**:
  - Creates a retriever for the local knowledge base.
  - Uses the retriever to search for documents related to the query.
  - Returns the search results as a list of `SearchResult` objects.

# Class Name: `StepPlanTopic`
- **Component Name**: `"plan_topic"`
- **Short Description**: Generates a topic plan from the provided content.
- **Full Description**: Reads the content, usually a list of summaries of related documents, and generates a list of topics discussed in these documents along with instructions to write detailed sections about these topics.

**Functionality**
- **Purpose**: To create a list of topics and corresponding prompts for writing detailed sections based on the content.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `content`: The content to analyze.
    - `query_metadata`: Optional metadata for the query.
  - **Returns**: A `TopicList` containing the generated topics and prompts.
- **Process**:
  - Determines the number of sections and article style from flow options.
  - Constructs a prompt using the content and query.
  - Calls an inference API to generate the topic list.
  - Returns the topic list as a `TopicList` object.

# Class Name: `StepQueryRewrite`
- **Component Name**: `"query_rewrite"`
- **Dependencies**: None
- **Direct Flow Option Items**: Inherits flow option items from `AbstractStep`.

**Functionality**
- **Purpose**: To rewrite a query using a specified strategy section and query metadata.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `query_metadata`: Metadata for the query.
    - `rewrite_section`: Optional strategy section for rewriting.
  - **Returns**: A `Rewrite` object containing the rewritten query.
- **Process**:
  - Logs the status of the query rewriting process.
  - If no rewrite section is provided, it retrieves it from the strategy.
  - Uses the strategy to determine how to rewrite the query.
  - Returns the rewritten query as a `Rewrite` object.

# Class Name: `StepRerank`
- **Component Name**: `"rerank"`
- **Dependencies**: None
- **Direct Flow Option Items**: None

**Functionality**
- **Purpose**: To rerank search result segments using a specified strategy section.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `top_ranked_result_segments`: List of top-ranked search result segments.
  - **Returns**: A list of reranked `SearchResultSegment` objects.
- **Process**:
  - Retrieves the rerank strategy section from the execution information.
  - If no strategy is provided or if it is disabled, it skips reranking.
  - Uses the strategy to rerank the search results.
  - Returns the reranked search result segments.

# Class Name: `StepScrapeUrlsToDocSource`
- **Component Name**: `"scrape_urls_to_docsource"`
- **Short Description**: Scrapes specified URLs to the target `DocSource`.
- **Full Description**: Uses a web searcher, a list of URLs, and a `DocSource` to scrape the URLs and save them as a list of `DocSinks` in the `DocSource`.

**Functionality**
- **Purpose**: To scrape URLs and create documents for an existing `DocSource`.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `web_searcher`: The `WebSearcher` instance to use.
    - `links`: List of URLs to scrape.
    - `docsource`: The document source to create documents for.
  - **Returns**: A dictionary of successfully created `Document` objects, keyed by URL.
- **Process**:
  - Uses the `WebSearcher` to scrape URLs and create `DocSinks`.
  - Processes the `DocSinks` to create `Document` objects.
  - Returns a dictionary of successfully created documents.

# Class Name: `StepSearchMedium`
- **Component Name**: `"search_medium"`
- **Short Description**: Searches Medium.com to get related articles and return their IDs.
- **Full Description**: Creates a list of article IDs with web search from Medium.com.

**Functionality**
- **Purpose**: To search Medium.com for articles related to specified keywords and return a list of article IDs.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `search_keywords`: Optional search keywords. If not provided, the original query from the chat query item will be used.
  - **Returns**: A list of `MediumArticle` objects containing the article IDs and other metadata.
- **Process**:
  - Uses a `WebSearcher` to perform a search on Medium.com with the specified keywords.
  - Extracts article IDs from the search results.
  - Uses a `WebScraper` to scrape and parse the articles for additional metadata.
  - Returns a list of `MediumArticle` objects with the collected data.

# Class Name: `StepSearchToDocsource`
- **Component Name**: `"search_to_docsource"`
- **Short Description**: Searches the web for related documents and saves them to the `DocSource`.
- **Full Description**: Creates a document source with web search. If the knowledge base has `auto_schedule` set to `True`, the document source will be scheduled for processing. Otherwise, it will be processed immediately.

**Functionality**
- **Purpose**: To create a document source by searching the web and processing the results.
- **Method**: `run_step`
  - **Parameters**:
    - `exec_info`: Execution information.
    - `search_keywords`: Optional search keywords. If not provided, the original query from the chat query item will be used.
    - `schedule_config`: Optional schedule configuration for the document source.
  - **Returns**: A `DocSource` object representing the created document source.
- **Process**:
  - Determines whether to include local data in the search.
  - Creates a document source for the search.
  - If `auto_schedule` is enabled, schedules the document source for processing.
  - If `auto_schedule` is disabled, processes the document source immediately.
  - Returns the created `DocSource`.
