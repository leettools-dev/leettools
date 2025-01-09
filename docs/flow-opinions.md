## **Feature: Opinions**

**Description:**

The **Opinions** workflow in LeetTools is designed to help users gather and analyze both factual information and subjective opinions on a given topic. This feature queries the web or local knowledge bases (KBs) for relevant content, processes the data to identify key facts and sentiments, and then combines them to generate a comprehensive report on the subject. It's particularly useful for obtaining a balanced view of a topic by capturing both factual data and emotional or subjective insights.

### **How it Works:**

1. **Topic Query and Web Search:**
   - **Local KB Search:** If a local KB is provided (`docsource_uuid`), the query is executed within it, retrieving the top segments that match the topic.
   - **Web Search:** If no KB is specified, a search is performed on the web using a specified search engine (e.g., Google). The results include web pages that provide relevant information on the topic.
2. **Crawling and Scraping:**
   - The workflow scrapes the top web pages or KB entries to collect relevant content for analysis.
   - This content is saved to a local KB for further processing, ensuring that all scraped data is preserved for reference.
3. **Sentiment and Fact Extraction:**
   - For each scraped page, the workflow scans the content to identify sentiments (positive, negative, or neutral) and factual data points.
   - The extracted facts and sentiments are stored in a database and combined to create a balanced representation of the topic.
4. **Dedupe and Combine:**
   - Duplicate sentiments and facts are removed to ensure that only unique data points are included in the final report.
   - The sentiments and facts are then combined into a coherent summary.
5. **Report Generation:**
   - A final report is generated, containing both the key facts and sentiments associated with the topic. This allows users to quickly understand different perspectives on the issue.
6. **Customization Options:**
   Users can customize the behavior of the **Opinions** workflow with several options:
    - `days_limit`: Limit search results to content published within a specific time range.
    - `excluded_sites`: Exclude certain websites from the search results.
    - `opinions_instruction`: Provide backend settings to control how sentiments and facts are extracted.
    - `summarizing_model`: Specify the model used to summarize the scraped articles (default is `gpt-4o-mini`).
    - `writing_model`: Specify the model used to generate each section of the final report (default is `gpt-4o-mini`).
    - `search_max_results`: Limit the maximum number of search results retrieved from the web.
    - `search_iteration`: Control how many pages of search results to retrieve if the maximum number of results is not reached.
    - `search_language`: Specify the language of the search query.
7. **Result Output:**
   - The final report includes both facts and sentiments on the topic, which are clearly separated to provide users with an understanding of the topic from both an objective and emotional perspective.

### **Key Benefits:**

- **Comprehensive Analysis:** Combines facts and sentiments to provide a well-rounded view of the topic.
- **Customizable Workflow:** Control various aspects of the search and analysis process with multiple parameters.
- **Efficient Sentiment and Fact Extraction:** Uses AI models to accurately identify and extract relevant data points from large volumes of text.
- **Time-Sensitive Information:** Filter results by time range to gather only the most relevant and up-to-date content.

### **Example User Case:**

To analyze the topic of "AI in Healthcare" and generate a report with a summary of facts and sentiments, you can run the following command:

```bash
% leet flow -t opinions -q "AI in Healthcare" -l info -p search_max_results=20 -p days_limit=30 -k "AI in Healthcare"

```

### **Explanation:**

- `t opinions`: Specifies the **Opinions** workflow.
- `q "AI in Healthcare"`: The topic to analyze.
- `l info`: Sets the log level to `info`, showing essential log messages.
- `p search_max_results=20`: Limits the search to a maximum of 20 results.
- `p days_limit=30`: Filters search results to include only content from the past 30 days.

---

This workflow provides an efficient way to gather and analyze both factual information and public opinions about a topic, helping users get a comprehensive understanding of the subject matter. 