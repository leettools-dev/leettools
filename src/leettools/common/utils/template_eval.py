from typing import Any, Dict

from jinja2 import BaseLoader, Environment, TemplateSyntaxError, UndefinedError, meta

from leettools.common import exceptions
from leettools.common.logging import logger


def render_template(template_str: str, variables: Dict[str, Any]) -> str:
    try:
        # Create an environment with a BaseLoader to prevent autoescaping,
        # which is useful for non-HTML templates
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
    """
    variables = {"name": "John Doe", "items": ["Apple", "Banana", "Cherry"]}

    result = render_template(template_str, variables)
    print(result)

    variables = find_template_variables(template_str)
    print(variables)
