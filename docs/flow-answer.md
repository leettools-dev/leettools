## Feature: Answer

Description:

The Answer workflow in LeetTools is designed to provide direct answers to user queries, enriched with source references. It searches through local knowledge bases (KBs) or the web, retrieving the most relevant information to answer the query effectively. With configurable options, users can tailor the answer generation process to their specific needs, including the style of the answer, language, and source filtering.

### How it Works:

1. Query Processing:

   The workflow initiates by receiving a query, which can either be targeted at a local knowledge base (KB) or the web (the entire web or specific targeted websites). If a local KB is specified, the system searches the relevant content; otherwise, it pulls the query results from the web via a search engine (e.g., Google).

2. Retriever Mechanism:

   - Local KB Search: If a local KB is provided, the query is directed towards it, using the specified `docsource_uuid` for targeted searches.
   - Web Search: When no KB is specified, the workflow performs a web search to fetch top documents that are most likely to contain relevant information for the query. The search behavior can be further customized with parameters like `retriever_type` (e.g., Google) and `excluded_sites` (to avoid specific domains).
   - Fallback Search: If web search yields no relevant results, the system automatically falls back to searching specified KBs. This ensures comprehensive coverage by leveraging both web and local knowledge sources for optimal results.

3. Document Pipeline:

   The fetched search results are processed through the document pipeline, which includes:

   - Conversion: Raw documents are transformed into a structured format.
   - Chunking: Large documents are divided into smaller, manageable segments.
   - Indexing: These segments are indexed for quick retrieval.

4. Contextual Retrieval:

   Based on the user query, the workflow retrieves the most relevant segments from the indexed KB or web results. These segments are then concatenated to create a cohesive context, providing the LLM with detailed background information.

5. Answer Generation:

   Using the context formed from the retrieved segments, the LLM generates an answer to the query. The answer is generated with high accuracy and is accompanied by source references, ensuring transparency and credibility. Additional parameters enhance the answer customization:

   - Article Style (`article_style`): Choose from various output styles, such as analytical research reports, humorous news articles, or technical blog posts. The default style is analytical research reports.
   - Word Count (`word_count`): Control the length of the generated answer, or leave it empty for automatic word count adjustment.
   - Language (`output_language`): Specify the language in which the result should be output.
   - Reference Style (`reference_style`): Select the reference style, such as default or news, for the citations in the answer.
   - Strict Context (`strict_context`): Determine whether the LLM should strictly adhere to the context when generating the answer.
   - Example Output (`output_example`): Provide an example of the expected output, guiding the LLM to align with the desired response style.

6. Search Customization:

   The web search process can be finely tuned with the following options:

   - Search Iteration (`search_iteration`): If the initial results do not meet expectations, you can define how many additional pages the search should explore.
   - Search Max Results (`search_max_results`): Limit the number of search results returned by the retriever.
   - Target Site (`target_site`): Limit the search to a specific website if needed.
   - Days Limit (`days_limit`): Limit the search to a specified number of days, or leave it empty for no time restriction.

### Key Benefits:

- Customization: Fine-tune your search and answer generation with options such as output style, word count, language, and reference format.
- Efficiency: Automate the search and answer generation process, reducing manual work.
- Contextual Accuracy: By leveraging contextual retrieval and LLM-based response generation, answers are both precise and comprehensive.
- Transparency: Source references are provided alongside the answers for verification and reliability.

### Example Use Case:

To search for an answer related to "Quantum Computing", you can specify:

- Article Style as "technical blog post"
- Word Count as 500 words
- Language as English
- Excluded Sites like "example.com"
- Target Site as "news.ycombinator.com"
- Knowledge Base as "quantum_kb" (if not exists, a new KB will be created to store search results)

These parameters allow you to tailor the results to match your needs while ensuring relevant, high-quality answers.

Try this command in your terminal:

```bash
leet flow -t answer -q "What is Quantum Computing?" -k quantum_kb -l info -p article_style="technical blog post" -p word_count=500 -p output_language="en" -p excluded_sites="example.com" -p target_site="news.ycombinator.com" 
```



