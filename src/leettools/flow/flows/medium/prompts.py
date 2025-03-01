QUERY_PROMPT = """
Given the topic description {topic} input by user, generate a search query for google to search 
for Medium articles about this topic. The result should be a query string that can be used to search.
The query string should always in English no matter what language the topic is. 

Don't include the following words in the return search query:
articles

The search query should be common search queries, for example:
If the topic is "I am interested in RAG related articles", the returned query should be "RAG".
If the topic is "find out the recipes for fried chicken", the returned query should be "fried chicken recipes".
If the topic is "I plan to visit Japan next month, what should I do?", the returned query should be "Japan travel tips".

**Output Format:**
Provide the output as a JSON object with the following structure and keys:
- `query`: the search query for google to search for articles about the topic. Don't include the site information.
"""

SUMMARY_PROMPT = """
You are an assistant that creates structured writing suggestions for Medium articles in Markdown format. 
The following is the topic that a user is interested in:
{topic}

**Task:**
Using the collected popular Medium articles, generate a new writing idea based on the topic and the collected data:
1. Generate a blog title that is catchy, engaging, and SEO friendly.
2. Generate a blog outline that is detailed and well-structured.
3. For each section of the outline, provide specific strategies and techniques to enhance reader engagement and differentiate the content from other popular articles on the same topic. 
Include actionable tips on style, unique perspectives, and value-added information that can make each section stand out.
4. Use **MarkDown** format to organize the writing idea. 

**Output Format:**
Provide the output as a organized text with *MarkDown* format by following the structure below:
1. **Headings:**
   - Don't use #, ## and ### as the headings, starting from #### instead.
   - Ensure the main title uses the top-level heading (`####`) and subheadings use descending levels (`#####`, `######`, etc.) to represent hierarchy.
   - Use appropriate heading levels (`####`, etc.) without redundant bold (`**`) or italic (`*`) formatting.

2. **Horizontal Rules:**
   - Remove unnecessary horizontal rules (`---`) unless they semantically separate major sections.
   - Use headings and spacing to organize content instead of horizontal lines.

3. **Bold and Italic Text:**
   - Use bold (`**`) and italic (`*`) formatting sparingly and only for emphasis where necessary.
   - Avoid redundant bolding in headings, as headings are already bold by default.

4. **Lists:**
   - Ensure ordered lists (`1.`, `2.`, etc.) and unordered lists (`-`, `*`) are properly nested with consistent indentation (two spaces per level).
   - Maintain uniform list styles and avoid mixing different list types unless required.

5. **Tables:**
   - Include all specified tables with correct Markdown table syntax.
   - Ensure tables are properly formatted with pipes (`|`) and hyphens (`-`) to define headers and align columns.

6. **Quotation Marks:**
   - Remove unnecessary quotation marks around titles or headings unless they are part of the intended text.

7. **Consistency:**
   - Maintain consistent formatting throughout the document.
   - Ensure uniform spacing, indentation, and styling for all elements.

8. **Validation:**
   - Double-check Markdown syntax to prevent any issues during HTML conversion.
   - Ensure there are no syntax errors, such as unclosed tags or improperly formatted elements.

9. **Additional Enhancements:**
   - If applicable, add semantic HTML elements (like `<strong>` for bold or `<em>` for italics) through Markdown for better accessibility.
   - Ensure that all links, if any, are correctly formatted using `[link text](URL)` syntax.

Below is the popular Medium articles collected as the reference for the writing idea:
**Collected Data:**
{collected_data}
"""
