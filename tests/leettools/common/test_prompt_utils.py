from leettools.common.utils import template_eval
from leettools.flow.utils import prompt_util


def test_prompt_direct():

    lang_instruction = prompt_util.lang_instruction()
    context = "This my context"
    prompt = f"""
{ lang_instruction }
{ prompt_util.json_format_instruction() }
{{
    "key": "context",
    "value": "{ context }"
}}
"""
    expected_output = """
using the same language as the query

Return the result in the following JSON format, ensuring the output is formatted as 
JSON data, and not in a JSON block:

{
    "key": "context",
    "value": "This my context"
}
"""
    assert prompt == expected_output


def test_prompt_without_fstr():
    prompt_template = """
{{ lang_instruction }}
{{ json_format_instruction }}
{
  "key": "context",
  "value": "{{ context }}"
}
"""

    # get the system suppored template variables
    template_vars = prompt_util.get_template_vars(
        flow_options={},
        inference_context="This is inference context",
        rewritten_query="This is rewritten query",
        lang="en",
    )
    # add more variables to the template_vars
    template_vars["context"] = "my customized context"

    prompt = template_eval.render_template(prompt_template, template_vars)

    expected_output = """
using the en language

Return the result in the following JSON format, ensuring the output is formatted as 
JSON data, and not in a JSON block:

{
  "key": "context",
  "value": "my customized context"
}"""  # have no idea why here we can't have a newline
    assert prompt == expected_output


def test_prompt_with_fstr():

    title = "What is the capital of France?"

    prompt_template = f"""
{{{{ lang_instruction }}}}
{{{{ reference_instruction }}}}

{title}

{{
  "key": "context",
  "value": "{{{{ context }}}}"
}}
"""

    # get the system suppored template variables
    template_vars = prompt_util.get_template_vars(
        flow_options={},
        inference_context="This is inference context",
        rewritten_query="This is rewritten query",
        lang="en",
    )

    prompt = template_eval.render_template(prompt_template, template_vars)

    expected_output = """
using the en language

In the answer, use format [1], [2], ..., [n] in line where the reference is used. 
For example, "According to the research from Google[3], ...". 
DO NOT add References section at the end of the output.


What is the capital of France?

{
  "key": "context",
  "value": "This is inference context"
}"""
    assert prompt == expected_output
