from typing import Any, Dict, List, Optional

from leettools.common.logging import logger
from leettools.common.utils import config_utils
from leettools.core.consts import flow_option
from leettools.flow import flow_option_items
from leettools.flow.flow_option_items import FlowOptionItem


def get_supported_template_option_items() -> List[FlowOptionItem]:
    return [
        flow_option_items.FOI_STRICT_CONTEXT(),
        flow_option_items.FOI_ARTICLE_STYLE(),
        flow_option_items.FOI_OUTPUT_EXAMPLE(),
        flow_option_items.FOI_WORD_COUNT(),
        flow_option_items.FOI_OUTPUT_LANGUAGE(),
    ]


def get_template_vars(
    flow_options: Dict[str, Any],
    inference_context: str,
    rewritten_query: str,
    lang: str,
) -> Dict[str, str]:
    """
    This function returns a dictionary that contains all the variable supported
    in the prompt instantiation.
    """
    display_logger = logger()

    template_vars = {
        "context": inference_context,
        "rewritten_query": rewritten_query,
        "lang": lang,
        "lang_instruction": lang_instruction(lang),
        "reference_instruction": reference_instruction(),
        "context_presentation": context_presentation(),
        "json_format_instruction": json_format_instruction(),
        "out_of_context_instruction": out_of_scope_instruction(),
    }

    strict_context = config_utils.get_bool_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_STRICT_CONTEXT,
        default_value=False,
        display_logger=display_logger,
    )

    if strict_context:
        template_vars["strict_context_instruction"] = strict_context_instruction()
    else:
        template_vars["strict_context_instruction"] = ""

    article_style = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_ARTICLE_STYLE,
        default_value=flow_option_items.FOI_ARTICLE_STYLE().default_value,
        display_logger=display_logger,
    )

    template_vars["style_instruction"] = style_instruction(article_style=article_style)

    output_example = config_utils.get_str_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_OUTPUT_EXAMPLE,
        default_value=None,
        display_logger=display_logger,
    )

    if output_example is not None:
        template_vars["ouput_example_instruction"] = ouput_example_instruction(
            output_example=output_example
        )
    else:
        template_vars["output_example_intruction"] = ""

    word_count = config_utils.get_int_option_value(
        options=flow_options,
        option_name=flow_option.FLOW_OPTION_WORD_COUNT,
        default_value=None,
        display_logger=display_logger,
    )

    if word_count is not None:
        template_vars["word_count_instruction"] = word_count_instruction(
            word_count=word_count
        )
    else:
        template_vars["word_count_instruction"] = ""

    return template_vars


def context_presentation() -> str:
    return """Given the context as a sequence of references with a reference id in the 
format of a leading [x],"""


def reference_instruction() -> str:
    return """
In the answer, use format [1], [2], ..., [n] in line where the reference is used. 
For example, "According to the research from Google[3], ...". 
DO NOT add References section at the end of the output.
"""


def lang_instruction(lang: Optional[str] = None) -> str:
    if lang is None or lang == "":
        lang_instruction = "using the same language as the query"
    else:
        lang_instruction = f"using the {lang} language"
    return lang_instruction


def json_format_instruction() -> str:

    # TODO: change all steps using this instruction to use the new API parameter
    return """
Return the result in the following JSON format, ensuring the output is formatted as 
JSON data, and not in a JSON block:
"""


def out_of_scope_instruction() -> str:
    return """
"The question is out of the scope of the context provided. Note that we only answer the
question based on the information in the knowledge base, if one piece of the information
asked is not in the KB, the system will refuse to answer the question. Use essay generator
or add related docsource to the KB to help answer the question."
"""


def strict_context_instruction() -> str:
    return """
Please create the answer strictly related to the context. If the context has no
information about the query, please write "No related information found in the context".
"""


def style_instruction(article_style: str) -> str:
    return f"""
Please try to write the section as part of {article_style}.
"""


def ouput_example_instruction(output_example: str) -> str:
    return f"""
Here is an example output and try to emulate the style:
{output_example}
"""


def word_count_instruction(word_count: int) -> str:
    return f"""
Limit the out to {word_count} words.
"""
