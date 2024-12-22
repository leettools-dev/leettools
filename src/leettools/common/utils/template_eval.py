from typing import Any, Dict, Optional

from jinja2 import (
    BaseLoader,
    Environment,
    TemplateSyntaxError,
    Undefined,
    UndefinedError,
    meta,
)

from leettools.common import exceptions
from leettools.common.logging import logger


class KeepPlaceholderUndefined(Undefined):
    def __str__(self):
        return f"{{{{ {self._undefined_name} }}}}"


def render_template(
    template_str: str, variables: Dict[str, Any], allow_partial: Optional[bool] = False
) -> str:
    """
    Render a Jinja2 template string with the given variables. If allow_partial is True,
    the template will be rendered even if some variables are missing. The missing variables
    will be replaced with placeholders. If allow_partial is False, an exception will be
    raised if any variables are missing.

    Args:
    - template_str: The Jinja2 template string.
    - variables: The variables to render the template with.
    - allow_partial: Whether to allow partial rendering. Defaults to False.

    Returns:
    - The rendered template string.
    """
    try:
        # Create an environment with a BaseLoader to prevent autoescaping,
        # which is useful for non-HTML templates
        if allow_partial:
            env = Environment(
                loader=BaseLoader(),
                autoescape=False,
                undefined=KeepPlaceholderUndefined,
            )
        else:
            env = Environment(loader=BaseLoader(), autoescape=False)
        template = env.from_string(template_str)
        return template.render(variables)
    except UndefinedError as e:
        logger().error(f"template_str: {template_str}")
        logger().error(f"variables: {variables}")
        raise exceptions.MissingParametersException(f"Error: Undefined variable. {e}")
    except TemplateSyntaxError as e:
        logger().error(f"template_str: {template_str}")
        logger().error(f"variables: {variables}")
        raise exceptions.UnexpectedCaseException(f"Error: Malformed template. {e}")
    except Exception as e:
        logger().error(f"template_str: {template_str}")
        logger().error(f"variables: {variables}")
        # Catch-all for any other Jinja2-related errors or general exceptions
        raise exceptions.UnexpectedCaseException(f"Unexpected error: {e}")


def find_template_variables(template_str: str) -> set[str]:
    env = Environment()
    ast = env.parse(template_str)
    # meta.find_undeclared_variables returns a set of all undeclared variables found in the AST
    undeclared_variables = meta.find_undeclared_variables(ast)
    return undeclared_variables


# Example usage
if __name__ == "__main__":
    template_str = """
    {% block header %}
    Hello {{ name }}!
    {% endblock %}
    
    {% block list %}
    {% for item in items %}
    - {{ item }}
    {% endfor %}
    {% endblock %}
    
    Undefined: {{ undefined_variable }}
    """
    variables = {"name": "John Doe", "items": ["Apple", "Banana", "Cherry"]}

    result = render_template(template_str, variables)
    print(result)
    print("===========================")

    result = render_template(template_str, variables, allow_partial=True)
    print(result)
    print("===========================")

    variables["undefined_variable"] = "This variable is now defined"
    result = render_template(template_str, variables)
    print(result)
    print("===========================")

    template_variables = find_template_variables(template_str)
    print(template_variables)
