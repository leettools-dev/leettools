from leettools.settings import SystemSettings

TABLE_PROMPT = """
Given the following piece of text obtained from a PDF file, which represents a table, 
please return a table in markdown format without changing its content.
If it is not a table, then return the text as is. Don't return anything else.

If the first line of this text starts with something like this: "| 1.1.1 introduction column | ...", 
please extract "1.1.1 introduction" as a heading in the markdown format and put
it at the beginning of the table. The "column" should be treated as part of the table header.
So "| 1.1.1 introduction column | ..." will be converted to:
### 1.1.1 introduction
| column | ...

If the first line starts like "| column1 something | ..." then there is no heading to extract.
So "| column1 something | ..." will be converted to:
|column1 something | ...

The extracted text from PDF you need to process is:
{table_text}
"""

TITLE_PROMPT = """
Given the following first few lines of text obtained from a PDF file. 
Please extract the title and return it in markdown format, 
remembering to add only one # in front of the title text:
# Some Title

Some Examples:
----------------
1. If the first few lines of the text are:
```
Prodcut Name
Version 1.0
Manual
```
Then the title to be extracted is "Product Name Version 1.0 Manual".
----------------
2. If the first few lines of the text are:
```
# Some unrelated text

We are presenting a new product called VWP 1.0, its ...
```
Then the title to be extracted is "Introducing VWP 1.0", which means you need to look into
the paragraph for the purpose of this article.
----------------
3. If the first few lines of the text are:
```
We, Company ABC, provide product CDF, as a major product in our line of products...
```
Then the title to be extracted is "Introducing CDF from ABC", which means you need to look into
the paragraph for the purpose of this article.
----------------
4. If the first few lines of the text are:
```
Company A product B

## feature list
```
Then the title to be extracted is "Company A product B feature list", which means you need to look into
the first line and the first heading to get the purpose of this article.
----------------
5. If the first few lines of the text are:
```
White Paper

Some introduction text
```
If the first line is something like "White Paper", or "User Manual", or "Product Manual", 
then the title to be extracted is just this first line: "White Paper" or "User Manual" or "Product Manual.
It means in this case, you only need to look into the first line to get the purpose of this article.
----------------
6. If the first few lines of the text are:
```
## Company A

A leading company in the xxx industry

At company A, we are committed to providing the best products and services to our customers...
```
In this case, the title to be extracted is "Company A:  A leading company in the xxx industry", 
which means you need to look into the company name and the followed description of this company.
----------------

Remember return one line with a prefix "Title:" in front of the title text. No other lines are allowed.


The extracted text you need to process is:
{text}
"""


def _query_openai(settings: SystemSettings, prompt: str) -> str:
    """
    Queries the OpenAI API with the given prompt and returns the response.

    Args:
        prompt: The prompt to be queried.

    Returns:
        The response from the OpenAI API.
    """
    # TODO: use correct OpenAI provider info.

    from openai import OpenAI

    openai_client = OpenAI(
        base_url=settings.DEFAULT_LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )
    chat_completion = openai_client.chat.completions.create(
        temperature=0.0,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=settings.DEFAULT_INFERENCE_MODEL,
    )
    return chat_completion.choices[0].message.content


def parse_table(settings: SystemSettings, table_text: str) -> str:
    """
    Extracts the title from the text and returns it in markdown format.

    Args:
        text: The text from which the title is to be extracted.

    Returns:
        The title in markdown format.
    """
    if settings.OPENAI_UTILS_ENABLED:
        table_prompt = TABLE_PROMPT.format(table_text=table_text)
        title = _query_openai(table_prompt)
    else:
        parsed_table = table_text
    return parsed_table


def extract_title(settings: SystemSettings, header_test: str) -> str:
    if settings.OPENAI_UTILS_ENABLED:
        title_prompt = TITLE_PROMPT.format(text="\n".join(header_test))
        title = _query_openai(title_prompt)
    else:
        title = ""
    return title
