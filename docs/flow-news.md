## **Feature: News**

**Description:**

The **News** workflow in LeetTools helps users generate a list of the latest news items related to a specific topic from an updated local knowledge base (KB). This feature focuses on finding, consolidating, and ranking the most relevant news items, ensuring that users are kept up-to-date with the latest information. The workflow performs multiple steps to ensure that duplicate items are removed, and news items are ranked based on the number of sources reporting them.

### **How it Works:**

1. **KB Check and Document Retrieval:**
   - The workflow checks the KB for the most recently updated documents.
   - It scans these documents to find news items, focusing on newly added or modified content.
2. **Combining Similar News Items:**
   - News items with similar content are grouped together, reducing redundancy and improving clarity.
   - The grouping ensures that multiple sources reporting the same news are combined into a single news item.
3. **Removing Duplicates:**
   - Any news items that have already been reported are removed from the results, ensuring that users only receive fresh updates.
4. **Ranking by Source Count:**
   - The remaining news items are ranked based on the number of sources reporting them. This ensures that the most widely covered news items are given higher priority.
5. **Generate News List:**
   - A final list of news items is generated, each with references to the sources where the news was reported. This allows users to access the original documents for more detailed information.
6. **Customization Options:**
   Users can fine-tune the news generation process with several parameters:
    - `days_limit`: Limit the results to news published within a specific time range.
    - `article_style`: Specify the style of the generated news items, such as "news article" or "technical blog post" (default is "analytical research reports").
    - `output_language`: Specify the language for the output of the news items.
    - `word_count`: Control the number of words in the output sections (empty means automatic).
7. **Result Output:**
   - The final output is a list of relevant news items, ranked by source count, each containing references to the original reporting sources.

### **Key Benefits:**

- **Latest News:** Always retrieve the most up-to-date news from your local knowledge base.
- **Duplication-Free:** Duplicates are removed, so you only see unique news items.
- **Source Ranking:** News items are ranked by how many different sources report on them, ensuring you see the most important stories first.
- **Customization:** Adjust how news items are presented and filtered to meet your needs.

### **Example User Case:**

To generate a list of the most recent news on "AI in Healthcare" from your local KB, you can run the following command:

```bash
% leet flow -t news -q "Can we trust ai in Healthcare" -k "AI in Healthcare" -l info -p days_limit=30 -p article_style="news article" -p output_language="en"

```

### **Explanation:**

- `t news`: Specifies the **News** workflow.
- `l info`: Sets the log level to `info`, which provides essential log messages.
- `p days_limit=30`: Limits the news results to items published within the last 30 days.
- `p article_style="news article"`: Specifies the output style of the news items as a "news article."
- `p output_language="en"`: Outputs the results in English.

---

This workflow is ideal for users who want to stay informed about a specific topic, ensuring that they only receive fresh, relevant news while avoiding duplicate reporting. 