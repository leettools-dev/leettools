# Wrting a customized flow

# Different components
The following are the different components of the flow:

- utils: glue functions to handle data transformation, result generation, and etc.
- step: a single function step that performs a single action (an API call, an inference
  call, write to files, query DB, and etc).
- subflow: step combination that performs a sub-task, used by the flow to group related
  steps together and reuse them.
- iterator: iterates over a docource, a KB, or a list of them to perform a task.
- flow: sequence of steps that performs a task and return a result as the
  ChatQueryResultCreate data structure.
- executuor: implements the AbstractExcutor interface, mainly the execute_for_query 
  fucntion so that it can be served through the EDS API.

# Flow and Strategy
Each flow will be a python program that hooks up different types of steps to perform a
specific task. For each kind of step, it takes a specific kind of configuration (which
is the current strategy section) for the task.

The strategy specifies the configuration the steps use, such as the API or model 
parameters. Each strategy is separated into different sections, each section serving a 
specific purpose such as intention detecion, query rewrite, rerank, inference, and etc.
For some of the steps, they will multiple sections configuration. For example, the
section planning step can use the configuration for the inference step.


# Prompt templates

When defining the prompt templates, there are different types of variables that can be
used in the template.

## Create the final prompt directly

The final prompt can be created directly by using the f-string format in the template.
You can use variables and functions directly in the template, als need to use the double
curly braces to escape the curly braces in the f-string format.
```python
prompt = f"""
{ lang_instruction }
{ prompt_util.json_format_instruction() }
{{
  "key": "context",
  "value": "{ context }"
}}
"""
```

## Create a prompt template without the f-string format

The template will be renderd later in the system, so we have to use the double curly
braces to escape. Note that you need quadruple curly braces to escape the curly braces.

```python
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
  flow_options=flow_options,
  inference_context=content,
  rewritten_query=query,
  lang=output_lang,
)
# add more variables to the template_vars
template_vars['context'] = "my customized context"

prompt = template_eval.render_template(prompt_template, template_vars)
```

## Create a prompt template with variables with f-string format
 
In this case, we need to use the f-string format in the template to get variables in the
current context, and some other variables that will be provided at runtime. 

- {{{{ lang_instruction }}}} : these will be replaced at runtime using the variables
  provided by the prompt_util module.
- {{ }}: should be used to escape the curly braces in the f-string format.
- {title} : will be replaced with the title variable in the calling function.

For example, the following prompt template:

```python
title = "What is the capital of France?"

# if we have to use the title variable in the template using the f-string format
# single curly braces for f-string varaiables
# double curly braces to escape the curly braces for jason format
# quadruple curly braces to escape the template variables will be redenred later
prompt_template1 = f"""
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
  flow_options=flow_options,
  inference_context=content,
  rewritten_query=query,
  lang=output_lang,
)
# lang_instruction, reference_instruction, and context are variables that will be provided
prompt = template_eval.render_template(prompt_template, template_vars)
```

Note that lang_instruction and context are variables that will be provided at runtime
by the prompt_util module.

Check promt_util.py for more details on which variables and instructions are available.