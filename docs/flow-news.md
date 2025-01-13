## Feature: News

The **News** workflow in LeetTools helps users generate a list of the latest news items
related to a specific topic from an updated local knowledge base (KB). This feature
focuses on finding, consolidating, and ranking the most relevant news items, ensuring
that users are kept up-to-date with the latest information. The workflow ensures that
duplicate items are removed, and news items are ranked based on the number of sources
reporting them.

### How it Works:

1. KB Check and Document Retrieval:
   - The workflow checks the KB for the most recently updated documents.
   - It scans these documents to extract news items related to the topic.
2. Combining Similar News Items:
   - News items with similar content are clustered together.
   - The clustring ensures that multiple sources reporting the same news are combined 
      into a single news item.
1. Removing Previously Reported News:
   - Any news items that have already been reported before are removed from the results.
2. Ranking by Source Count:
   - The remaining news items are ranked based on the number of sources reporting them. 
      This ensures that the most widely covered news items are given higher priority.
3. Generate News List:
   - A final list of news items is generated, each with references to original url.
4. Customization Options:
   Users can fine-tune the news generation process with several parameters:
    - `days_limit`: Limit the results to news published within a specific time range.
    - `article_style`: Specify the style of the generated news items, such as "news article" or "technical blog post" (default is "analytical research reports").
    - `output_language`: Specify the language for the output of the news items.
    - `word_count`: Control the number of words in the output sections (empty means automatic).
5. Result Output:
   - The final output is a list of relevant news items, ranked by source count, each
      containing references to the original reporting sources.

### Key Benefits

- Latest News: Always retrieve the most up-to-date news from your local knowledge base.
- Duplication-Free: Duplicates are removed, so you only see unique news items.
- Source Ranking: News items are ranked by how many different sources report on them,
   ensuring you see the most important stories first.
- Customization: Adjust how news items are presented and filtered to meet your needs.

### Example User Case

To build a local KB with latest search results for the topic "LLM GenAI Startups", you
can setup the KB by adding a web search to the KB. When you need to generate the news item
list, you can ingest the search again and then generate the news list.

```bash
# add the search results to the KB
# this command will do the initial search and add the results to the KB
% leet kb add-search -k genai -q "LLM GenAI Startups" -d 1 -l info

# we can also add a url to the KB
% leet kb add-url -k genai -u "https://www.techcrunch.com" -l info

# this command will generate the list of news that happened within one day
% leet flow -t news -q "LLM GenAI Startups" -k genai  -p days_limit=1 -l info

# ingest the search results again next time before you generate the news list
% leet kb ingest -k genai -l info
```

### Set up Automation

Coming soon! We can set up a service to run the ingestion and news generation automatically.
