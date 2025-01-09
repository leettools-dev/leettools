## **Feature: Extract**

Description:

The Extract workflow in LeetTools allows users to extract structured data from search results—whether they come from a local knowledge base (KB) or the web. After performing the search and processing the results through the document pipeline (conversion, chunking, and indexing), this workflow extracts relevant data points from the matched documents and outputs them in a user-specified format (CSV, JSON, or Markdown). This is ideal for extracting information like company names, product details, investment rounds, and more from web pages or documents in the KB.

### **How it Works:**

1. **KB or Web Search**:
   - The workflow starts by performing a search using a retriever.
     - "Local" for querying the KB.
     - A web search engine (e.g., Google) fetches documents if no KB is specified.
   - If no existing KB is specified, an adhoc KB is created to save and process the results.
2. Document Processing:
   - New web search results are processed through the document pipeline: conversion, chunking, and indexing.
   - This ensures the data is ready for extraction.
3. Data Extraction:
   - Structured data is extracted based on a specified Pydantic model (see documentation for schema creation).
   - The model defines the exact data structure, making it possible to extract details such as product names, dates, locations, and other relevant fields.
4. **Out**put:
   - The extracted data is displayed in a structured format (CSV, JSON, or Markdown) according to the user's specifications.
   - Users can choose the output format with the `extract_output_format` parameter.
5. Saving Extracted Data:
   - By default, the extracted data is saved to the backend, preserving metadata such as the document’s URI and import time.
   - If this behavior is not desired, users can disable saving by setting `extract_save_to_backend=False`.
6. Customization Options:
   Users can adjust the extraction process with the following parameters:
    - `days_limit`: Limit the search to results from a specific time range.
    - `extract_output_format`: Choose the output format (e.g., CSV, JSON, or Markdown).
    - `extract_pydantic`: Define the schema for the target data using Pydantic models.
    - `output_language`: Specify the language for the output.
    - `image_search`: Limit the search to image results when searching the web.
    - `retriever_type`: Choose the retriever type (default is Google).
    - `search_max_results`: Set the maximum number of search results to retrieve.
7. Result Output:
   - The final output is a clean, structured table or file containing the extracted data, ready for analysis or further processing.

### **Key Benefits:**

- **Structured Data:** Easily extract structured information from unstructured web or KB content.
- **Customizable Output:** Choose the output format (CSV, JSON, or Markdown) that best suits your needs.
- **Flexible Search:** Use local KB or web search with a variety of retrievers (Google, etc.).
- **Schema-based Extraction:** Extract only the data you need by defining the schema with Pydantic models.
- **Data Saving:** Optionally save extracted data to the backend with relevant metadata.

### **Example User Case:**

To extract information related to "AI in Healthcare" from the web and output the data in CSV format, you can use the following command:

```bash
% leet flow -t extract -q "Comapny doing AI in Healthcare" -k "AI in Healthcare" -l info -p days_limit=30 -p extract_output_format=csv -p extract_pydantic="docs/company.py" -p output_language="en"

```

### **Explanation:**

- `t extract`: Specifies the Extract workflow.
- `q "Company doing AI in Healthcare"`: The search query to extract relevant data.
- `l info`: Sets the log level to `info`, which provides essential log messages.
- `p days_limit=30`: Limits the search to items published within the last 30 days.
- `p extract_output_format=csv`: Outputs the extracted data in CSV format.
- `p extract_pydantic="docs/company.py"`: Specifies the path to the Pydantic model for structured extraction.
- `p output_language="en"`: Outputs the results in English.

```python
class Company(BaseModel):
    name: str
    description: str
    industry: str
    main_product_or_service: str
```

### Attributes (Fields) of `Company`:

- `name: str`: This attribute stores the name of the company, and it is expected to be a string.
- `description: str`: This attribute stores a description of the company, and it is expected to be a string.
- `industry: str`: This field represents the industry that the company belongs to (e.g., "Technology," "Healthcare"), and it is also expected to be a string.
- `main_product_or_service: str`: This field represents the main product or service offered by the company (e.g., "Cloud Computing," "Medical Devices"), and it should be a string as well.

---

This workflow is highly useful for data extraction, especially for tasks that require the systematic collection of structured information from large sets of documents or web pages. 