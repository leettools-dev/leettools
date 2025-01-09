## **Feature: Search**

**Description:**

The **Search** workflow in LeetTools enables users to search for and retrieve the top segments of documents that match a given query. The workflow utilizes a combination of search techniques, including hybrid search (full-text and vector search) to return the most relevant results. It supports searching in both local knowledge bases (KB) and the web, and provides links to the original documents for easy reference.

### **How it Works:**

1. **Query and Search Mechanism:**
   - **Local KB Search:** If a local knowledge base (KB) is provided (`docsource_uuid`), the query is executed within it using a hybrid search approach, combining full-text search with vector-based search methods like SPLADE and Vector Cosine similarity.
   - **Web Search:** If no KB is provided, the workflow will search the web using a search engine (e.g., Google). You can specify custom search behaviors, such as excluding certain websites (`excluded_sites`) or limiting the search to specific sites (`target_site`).
2. **Document Pipeline:**
   - Search results are processed through the document pipeline, which includes **conversion**, **chunking**, and **indexing** of the fetched content.
   - Each document is divided into smaller segments for easier matching with the query.
3. **Hybrid Search:**
   - The search results are ranked and scored based on relevance using a combination of SPLADE and Vector Cosine similarity.
   - The top matching segments are returned along with their ranking score and links to the original documents.
4. **Customization Options:**
   Users can customize the search behavior with several options, including:
    - `days_limit`: Limit the search results to documents within a certain time range (useful for recent content).
    - `excluded_sites`: Specify a comma-separated list of sites to exclude from the search results.
    - `image_search`: Restrict the search to image results (default is false).
    - `recursive_scrape`: Enable recursive scraping to gather additional content from top URLs found in the initial search results.
    - `retriever_type`: Choose the retriever for web searches (default is `google`).
    - `search_max_results`: Control the maximum number of search results to retrieve (default is 10).
    - `search_iteration`: Control how many times the search process should go to the next page of results if the maximum number of results is not reached.
    - `search_language`: Specify the language for the search query, if the search API supports it.
    - `target_site`: Limit the search to a specific site or domain (useful for narrowing search results).
5. **Result Output:**
   - The workflow returns the top-ranked segments that match the query, including links to the original documents. This allows users to easily navigate to the full content for further reading.

### **Key Benefits:**

- **Relevance and Precision:** Hybrid search techniques (full-text + vector search) ensure that the most relevant results are returned with high accuracy.
- **Customizable Search Parameters:** Fine-tune your search with various parameters, such as search language, excluded sites, and recursive scraping.
- **Efficient Search:** Quickly retrieves top matching segments and provides easy access to the full documents with their original links.
- **Enhanced Search Logic:** Uses SPLADE and Vector Cosine similarity to rank documents, ensuring that results are based on both semantic and keyword relevance.

### **Example User Case:**

To search for top segments related to "Quantum Computing" and exclude results from a specific website, you can run the following command:

```bash
leet flow -t search -q "What is Quantum Computing?" -l info -p search_max_results=15 -p search_iteration=2
```

### **Explanation:**

- `t search`: Specifies the **Search** workflow.
- `q "What is Quantum Computing?"`: The query to search for segments related to Quantum Computing.
- `l info`: Sets the log level to `info`, showing essential log messages.
- `p search_max_results=15`: Limits the search to a maximum of 15 results.
- `p search_iteration=2`: Allows the search to go two pages deep for additional results.

---

This command searches for the top segments related to your query and excludes results from the specified site, ensuring that the search results are highly relevant to your needs. 