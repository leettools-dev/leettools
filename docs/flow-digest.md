## **Feature: Digest**

**Description:**

The **Digest** workflow in LeetTools is designed to generate a comprehensive, multi-section digest article based on search results. Whether you're researching a topic or compiling relevant information, this feature helps you gather, summarize, and organize content into an easy-to-read digest, all with customizable options to suit your specific needs.

### **How it Works:**

1. **Query and Content Filtering:**

   The user initiates the workflow by defining a search query. Optionally, the user can provide content instructions (`content_instruction`) to assess the relevance of the result documents. This helps refine the selection of content to be included in the digest article.

2. **Retriever Mechanism:**

   - **Local KB Search:** If a local knowledge base (KB) is specified (`docsource_uuid`), the system queries it directly.
   - **Web Search:** If no KB is provided, the workflow searches the web using a search engine (e.g., Google). Customizations like `excluded_sites` (to filter out specific domains) or `target_site` (to restrict searches to a specific website) can be applied.

3. **Document Pipeline:**

   The documents fetched through the search process are then passed through the document pipeline:

   - **Conversion:** Raw documents are transformed into a structured format.
   - **Chunking:** The documents are broken down into smaller, digestible segments.
   - **Indexing:** These segments are indexed for efficient retrieval.

4. **Summarization and Topic Planning:**

   Each document in the search results is summarized using an LLM API call. A topic plan for the digest article is then generated based on these summaries. The user can specify the number of sections (`num_of_sections`) for the article or let the planning agent decide automatically.

5. **Section Creation:**

   The digest article is divided into sections based on the topic plan. Content from the KB or the web is used to fill in each section. The sections are then concatenated into a cohesive article.

6. **Customization Options:**

   Users can fine-tune the output using the following parameters:

   - **Article Style (`article_style`)**: Choose from various output styles, such as analytical research reports, humorous news articles, or technical blog posts.
   - **Language (`output_language`)**: Output the result in a specific language.
   - **Word Count (`word_count`)**: Specify the desired word count for each section.
   - **Recursive Scraping (`recursive_scrape`)**: Enable recursive scraping to gather additional content from URLs found in the search results.
   - **Search Customizations**: Control search behavior with options like `search_max_results`, `search_iteration`, and `scrape_max_count`.

7. **Final Article Generation:**

   After generating and organizing the sections, the digest article is composed and returned in the specified format, complete with references and citations based on the chosen `reference_style`.

### **Key Benefits:**

- **Organized Content:** Automatically generates a well-structured, multi-section digest article, perfect for research or content curation.
- **Customization:** Fine-tune the article style, word count, search behavior, and more to suit your specific needs.
- **Efficient Research:** Combine relevant information from various sources into a cohesive article with minimal manual effort.
- **Transparency:** Include references in the output with customizable citation styles, ensuring the credibility of the content.

### **Example User Case:**

To generate a digest article on "Quantum Computing," you can run the following command:

```bash
leet flow -t digest -q "What is Quantum Computing?" -k quantum_kb -l info -p article_style="analytical research reports" -p num_of_sections=5 -p output_language="en" -p recursive_scrape=True -p search_max_results=15 -p search_iteration=2
```

### **Explanation:**

- `t digest`: Specifies the **Digest** workflow.
- `q "What is Quantum Computing?"`: The search query for the digest article.
- `k quantum_kb`: Saves the scraped web pages to the knowledge base `quantum_kb`.
- `l info`: Sets the log level to `info`, showing essential log messages.
- `p article_style="analytical research reports"`: Sets the output style to an analytical research report.
- `p num_of_sections=5`: Specifies that the digest should have 5 sections.
- `p output_language="en"`: Outputs the article in English.
- `p recursive_scrape=True`: Enables recursive scraping of URLs found in the search results.
- `p search_max_results=15`: Limits the search to a maximum of 15 results.
- `p search_iteration=2`: Allows the search to go two pages deep for additional results.