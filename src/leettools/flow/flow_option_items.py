from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from leettools.context_manager import Context
from leettools.core.consts.flow_option import (
    FLOW_OPTION_ARTICLE_STYLE,
    FLOW_OPTION_CONTENT_INSTRUCTION,
    FLOW_OPTION_CONTEXT_LIMIT,
    FLOW_OPTION_DAYS_LIMIT,
    FLOW_OPTION_EXCLUDED_SITES,
    FLOW_OPTION_EXTRACT_INSTRUCTION,
    FLOW_OPTION_EXTRACT_JSON_SCHEMA_DEPRCATE,
    FLOW_OPTION_EXTRACT_KEY_FIELDS,
    FLOW_OPTION_EXTRACT_OUTPUT_FORMAT,
    FLOW_OPTION_EXTRACT_PYDANTIC,
    FLOW_OPTION_EXTRACT_PYTHON_INSTRUCTION,
    FLOW_OPTION_EXTRACT_SAVE_TO_BACKEND,
    FLOW_OPTION_EXTRACT_TARGET_MODEL_NAME,
    FLOW_OPTION_EXTRACT_VERIFY_FIELDS,
    FLOW_OPTION_IMAGE_SEARCH,
    FLOW_OPTION_NUM_OF_SECTIONS,
    FLOW_OPTION_OUTPUT_EXAMPLE,
    FLOW_OPTION_OUTPUT_LANGUAGE,
    FLOW_OPTION_PLANNING_MODEL,
    FLOW_OPTION_RECURSIVE_SCRAPE,
    FLOW_OPTION_RECURSIVE_SCRAPE_ITERATION,
    FLOW_OPTION_RECURSIVE_SCRAPE_MAX_COUNT,
    FLOW_OPTION_REFERENCE_STYLE,
    FLOW_OPTION_RETRIEVER_TYPE,
    FLOW_OPTION_SEARCH_ITERATION,
    FLOW_OPTION_SEARCH_LANGUAGE,
    FLOW_OPTION_SEARCH_MAX_RESULTS,
    FLOW_OPTION_SEARCH_REWRITE,
    FLOW_OPTION_STRICT_CONTEXT,
    FLOW_OPTION_SUMMARIZING_MODEL,
    FLOW_OPTION_TARGET_SITE,
    FLOW_OPTION_WORD_COUNT,
    FLOW_OPTION_WRITING_MODEL,
)
from leettools.flow.flow_component_type import FlowComponentType


class FlowOptionItem(BaseModel):
    """
    Option item for FlowComponent.
    """

    name: str = Field(..., description="The name of the variable.")

    flow_components: Optional[Dict[FlowComponentType, List[str]]] = Field(
        None, description="The flow components that use this variable."
    )

    display_name: Optional[str] = Field(
        None, description="The display name of the variable."
    )
    description: Optional[str] = Field(
        None, description="The description of the variable."
    )
    default_value: Optional[str] = Field(
        None, description="The default value of the variable."
    )
    value_type: Optional[str] = Field(
        "str",
        description="The type of the value," "currently support str, int, float, bool.",
    )
    required: Optional[bool] = Field(
        False,
        description="Whether the variable is required or not.",
    )
    explicit: Optional[bool] = Field(
        False,
        description="Whether the variable should be explicitly set by the user or not.",
    )
    multiline: Optional[bool] = Field(
        False,
        description="Whether the variable should be displayed in multiple lines or not.",
    )
    example_value: Optional[str] = Field(
        None,
        description="The example value of the variable, if no default is provided.",
    )
    code: Optional[str] = Field(
        None,
        description=(
            "If the value should be shown and edited as the specified programming "
            "code, such as Python, Markdown. Default is None."
        ),
    )
    code_variables: Optional[str] = Field(
        None, description=("The variables the code should provide to the backend.")
    )


def _planning_model(
    context: Optional[Context] = None,
    explicit: Optional[bool] = False,
    required: Optional[bool] = False,
) -> FlowOptionItem:
    if context is None:
        default_model = None
    else:
        default_model = context.settings.DEFAULT_PLANNING_MODEL

    return FlowOptionItem(
        name=FLOW_OPTION_PLANNING_MODEL,
        display_name="Planning Model",
        description="The model used to do the article planning.",
        default_value=default_model,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _summary_model(
    context: Optional[Context] = None,
    explicit: Optional[bool] = False,
    required: Optional[bool] = False,
) -> FlowOptionItem:
    if context is None:
        default_model = None
    else:
        default_model = context.settings.DEFAULT_PLANNING_MODEL
    return FlowOptionItem(
        name=FLOW_OPTION_SUMMARIZING_MODEL,
        display_name="Summarizing Model",
        description="The model used to summarize each article.",
        default_value=default_model,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _writing_model(
    context: Optional[Context] = None,
    explicit: Optional[bool] = False,
    required: Optional[bool] = False,
) -> FlowOptionItem:
    if context is None:
        default_model = None
    else:
        default_model = context.settings.DEFAULT_PLANNING_MODEL
    return FlowOptionItem(
        name=FLOW_OPTION_WRITING_MODEL,
        display_name="Writing Model",
        description="The model used to generating each section.",
        default_value=default_model,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _retriever(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_RETRIEVER_TYPE,
        display_name="Retriever",
        description="The type of retriever to use for the web search.",
        default_value="google",
        value_type="str",
        example_value="google",
        explicit=explicit,
        required=required,
    )


def _content_instruction(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_CONTENT_INSTRUCTION,
        display_name="Content Instruction",
        description=(
            "The relevance of the result documents from keyword search is assessed "
            "by the content instruction if provided. "
        ),
        default_value=None,
        value_type="str",
        example_value="",
        multiline=True,
        explicit=explicit,
        required=required,
    )


def _days_limit(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_DAYS_LIMIT,
        display_name="Days Limit",
        description=(
            "Number of days to limit the search results. "
            "0 or empty means no limit. "
            "In local KB, filters by the import time."
        ),
        default_value=None,
        value_type="int",
        explicit=explicit,
        required=required,
    )


def _search_max_results(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_SEARCH_MAX_RESULTS,
        display_name="Max search Results",
        description=(
            "The maximum number of search results for retrievers to return. "
            "Each retriever may have different paging mechanisms. Use the parameter and "
            "the search iteration to control the number of results."
        ),
        default_value="10",
        value_type="int",
        explicit=explicit,
        required=required,
    )


def _search_rewrite(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_SEARCH_REWRITE,
        display_name="Rewrite Search Keywords",
        description=("Ask the LLM to generate search keywords from the search query."),
        default_value=None,
        value_type="bool",
        explicit=explicit,
        required=required,
    )


def _search_language(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_SEARCH_LANGUAGE,
        display_name="Search Language",
        description=(
            "The language used for keyword search if the search API supports."
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _output_language(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_OUTPUT_LANGUAGE,
        display_name="Output Language",
        description=("Output the result in the language."),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _output_example(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_OUTPUT_EXAMPLE,
        display_name="Output Example",
        description=(
            "The example of the expected output content. "
            "If left empty, no example will be provided to LLM."
        ),
        default_value=None,
        value_type="str",
        multiline=True,
        explicit=explicit,
        required=required,
    )


def _num_of_sections(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_NUM_OF_SECTIONS,
        display_name="Number of Sections",
        description=(
            "The number of sections in the output article. "
            "If left empty, the planning agent will decide automatically."
        ),
        default_value=None,
        value_type="int",
        explicit=explicit,
        required=required,
    )


def _article_style(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_ARTICLE_STYLE,
        display_name="Article Style",
        description=(
            "The style of the output article such as analytical research reports, humorous "
            "news articles, or technical blog posts."
        ),
        value_type="str",
        default_value="analytical research reports",
        example_value="analytical research reports",
        explicit=explicit,
        required=required,
    )


def _word_count(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_WORD_COUNT,
        display_name="Word Count",
        description="The number of words in the output section. Empty means automatics.",
        value_type="int",
        default_value=None,
        explicit=explicit,
        required=required,
    )


def _extract_instruction(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_INSTRUCTION,
        display_name="Extract Instruction",
        description=("Describe what information to extract from the content."),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
        multiline=True,
        example_value="""
If the article contains the information about a company, extract the following information:
- The company name
- The amount raised (in millions USD)
- The round type
- The investors
- The date of the round
- The company's main product or service
Use -1 for unknown numeric values and "n/a" for unknown string values.
If there are multiple companies in the article, extract all of them.
""",
    )


def _extract_pydantic(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_PYDANTIC,
        display_name="Extract Pydantic Model",
        description=(
            "The schema of the target data as a pydantic model, see https://docs.pydantic.dev"
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
        multiline=True,
        example_value="""class CompanyInfo(BaseModel):
    name: str
    description: str
    website: str
    main_product_or_service: str
""",
    )


def _extract_json_schema(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_JSON_SCHEMA_DEPRCATE,
        display_name="Extract Schema as JSON",
        description=(
            "The schema of the extracted information. Should be a JSON string."
            f"The schema should match the description in {FLOW_OPTION_EXTRACT_INSTRUCTION}."
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
        multiline=True,
        example_value="""
{
    "Company": {
        "name": "str",
        "amount_raised": "float",
        "round_type": "str",
        "investors": "List[str]",
        "round_date": "str",
        "main_product_or_service": "str"
    }
}
""",
    )


instructions_str = """
If the article contains the information about a company, extract the following information:
- The company name
- The amount raised (in millions USD)
- The round type
- The investors
- The date of the round
- The company's main product or service
Use -1 for unknown numeric values and "n/a" for unknown string values.
If there are multiple companies in the article, extract all of them.
"""


def _extract_python_instruction(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_PYTHON_INSTRUCTION,
        display_name="Extraction Instructions in Python",
        description=(
            "The instructions of the extractions in Python code. Right now the required "
            "variables are 'target_model_name' and 'instructions'. Also we need to specify "
            "the key fields and verify fields if needed."
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
        multiline=True,
        code="python",
        example_value=f"""
from pydantic import BaseModel

instructions = \"\"\"
{instructions_str}
\"\"\"

class Company(BaseModel):
    name: str
    amount_raised: float
    round_type: str
    investors: List[str]
    round_date: str
    main_product_or_service: str

target_model_name = "Company"
key_fields = ["name"]
""",
    )


def _extract_target_model_name(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_TARGET_MODEL_NAME,
        display_name="Target Pydantic Model Name used in the final list",
        description=(
            "There might be multiple Pydantic models in the schema definition. "
            "Specify which model to use for the final list."
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
        multiline=False,
        example_value="Comapny",
    )


def _extract_key_fields(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_KEY_FIELDS,
        display_name="Key Fields",
        description=(
            "Comma separated field names that identifies an object in the extraction. "
            "Extracted data with the same key fields will be considered of the same object. "
            "All extracted versions of the same object will be deduped based on them. "
            "The key fields should exist in the schema of the extracted information. "
            "If left empty, every extracted object will be considered unique."
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _extract_save_to_backend(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_SAVE_TO_BACKEND,
        display_name="Save extracted data to backend",
        description=(
            "Save the extracted data to the backend. Default True. If False, the "
            "extracted data will not be saved. The saved data will have the same "
            "schema specified in the pydantic model, plus metadata such as the "
            "import time and the original document URI."
        ),
        default_value="True",
        value_type="bool",
        explicit=explicit,
        required=required,
    )


def _extract_verify_fields(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_VERIFY_FIELDS,
        display_name="Verification Fields",
        description=(
            "Comma separated field names that need to be verified for the extracted objects. "
            "For example, although the address of a company is not in the key fields, and a "
            "company may have multiple addresses for different offices, we want to verify and "
            "dedup all the addresses extracted. If left empty, no verification will be performed."
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _extract_output_format(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXTRACT_OUTPUT_FORMAT,
        display_name="Output format",
        description=(
            "The output of the extracted data. Default is json. Currently also support "
            " csv, md."
        ),
        default_value=None,
        value_type="str",
        explicit=explicit,
        required=required,
    )


def _reference_style(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_REFERENCE_STYLE,
        display_name="Reference Style",
        description=(
            "The style of the references in the output article. Right now support "
            "news, default, and full."
        ),
        default_value=None,
        value_type="str",
        example_value="full",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _strict_context(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_STRICT_CONTEXT,
        display_name="Strict Context",
        description="When generating a section, whether to use strict context or not.",
        default_value="False",
        value_type="bool",
        example_value="False",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _target_site(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_TARGET_SITE,
        display_name="Target Site",
        description=(
            "When searching the web, limit the search to this site. "
            "Empty means search all sites."
        ),
        default_value=None,
        value_type="str",
        example_value="",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _search_iteration(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_SEARCH_ITERATION,
        display_name="Max iteration when using the web search retriever",
        description="If the max result is not reached, how many times we go to the next page.",
        default_value="3",
        value_type="int",
        example_value="3",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _recursive_scrape(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_RECURSIVE_SCRAPE,
        display_name="Recursive scrape",
        description="If true, scrape the top urls found in the search results documents.",
        default_value="False",
        value_type="bool",
        example_value="False",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _recursive_scrape_iteration(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_RECURSIVE_SCRAPE_ITERATION,
        display_name="Recursive scrape iteration",
        description=(
            "When we do recursive scraping, we will not stop until we reach the max "
            "number of results or the number of iterations specified here."
        ),
        default_value="3",
        value_type="int",
        example_value="3",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _recursive_scrape_max_count(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_RECURSIVE_SCRAPE_MAX_COUNT,
        display_name="Recursive scrape max item count",
        description=(
            "When we do recursive scraping, we will not stop until we reach the number of "
            "max iterations or the max number of results specified here."
        ),
        default_value="10",
        value_type="int",
        example_value="10",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _image_search(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_IMAGE_SEARCH,
        display_name="Image Search",
        description=("When searching on the web, limit the search to image search. "),
        default_value="False",
        value_type="bool",
        example_value="False",
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _search_excluded_sites(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_EXCLUDED_SITES,
        display_name="Excluded Site",
        description=(
            "List of sites separated by comma to ignore when search for the information. "
            "Empty means no filter."
        ),
        default_value=None,
        value_type="str",
        example_value=None,
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _query_docsource_uuid(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name="docsource_uuid",
        display_name="Docsource UUID",
        description="The docsource uuid to run the query on when querying local KB.",
        default_value=None,
        value_type="str",
        example_value=None,
        multiline=False,
        explicit=explicit,
        required=required,
    )


def _context_limit(
    explicit: Optional[bool] = False, required: Optional[bool] = False
) -> FlowOptionItem:
    return FlowOptionItem(
        name=FLOW_OPTION_CONTEXT_LIMIT,
        display_name="Context Limit",
        description="Override the context limit from the model info.",
        default_value=None,
        value_type="int",
        example_value=None,
        multiline=False,
        explicit=explicit,
        required=required,
    )


FOI_ARTICLE_STYLE = _article_style
FOI_CONTENT_INSTRUCTION = _content_instruction
FOI_CONTEXT_LIMIT = _context_limit
FOI_DAYS_LIMIT = _days_limit
FOI_DOCSOURCE_UUID = _query_docsource_uuid
FOI_EXTRACT_INSTRUCTION = _extract_instruction
FOI_EXTRACT_JSON_SCHEMA = _extract_json_schema
FOI_EXTRACT_KEY_FIELDS = _extract_key_fields
FOI_EXTRACT_OUTPUT_FORMAT = _extract_output_format
FOI_EXTRACT_PYDANTIC = _extract_pydantic
FOI_EXTRACT_PYTHON_INSTRUCTION = _extract_python_instruction
FOI_EXTRACT_PYTHON_TARGET_MODEL_NAME = _extract_target_model_name
FOI_EXTRACT_SAVE_TO_BACKEND = _extract_save_to_backend
FOI_EXTRACT_VERIFY_FIELDS = _extract_verify_fields
FOI_IMAGE_SEARCH = _image_search
FOI_NUM_OF_SECTIONS = _num_of_sections
FOI_OUTPUT_EXAMPLE = _output_example
FOI_OUTPUT_LANGUAGE = _output_language
FOI_PLANNING_MODEL = _planning_model
FOI_REFERENCE_STYLE = _reference_style
FOI_RETRIEVER = _retriever
FOI_SEARCH_EXCLUDED_SITES = _search_excluded_sites
FOI_SEARCH_LANGUAGE = _search_language
FOI_SEARCH_MAX_ITERATION = _search_iteration
FOI_SEARCH_MAX_RESULTS = _search_max_results
FOI_SEARCH_RECURSIVE_SCRAPE = _recursive_scrape
FOI_SEARCH_RECURSIVE_SCRAPE_ITERATION = _recursive_scrape_iteration
FOI_SEARCH_RECURSIVE_SCRAPE_MAX_COUNT = _recursive_scrape_max_count
FOI_SEARCH_REWRITE = _search_rewrite
FOI_STRICT_CONTEXT = _strict_context
FOI_SUMMARY_MODEL = _summary_model
FOI_TARGET_SITE = _target_site
FOI_WORD_COUNT = _word_count
FOI_WRITING_MODEL = _writing_model
