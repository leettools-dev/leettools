from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from leettools.common import exceptions
from leettools.common.logging import logger


def check_config(config: Dict[str, Any], key: str, err_msgs: List[str]) -> Any:
    """
    Get a value from a dictionary and check if it is not None.

    If the value is None, add an error message to the error message list.

    Args:
        data (Dict[str, Any]): The dictionary to get the value from.
        key (str): The key to get the value from.
        err_msgs (List[str]): The list of error messages.

    Returns:
        Any: The value from the dictionary.
    """
    value = config.get(key, None)
    if value is None:
        err_msgs.append(f"Field {key} not found in data.")
    return value


def execute_pydantic_snippet(code: str) -> Tuple[Dict[str, Any], Dict[str, type]]:
    """
    Executes a Pydantic code snippet in a local namespace and returns the resulting
    variable and type dictionaries.

    Args:
        code (str): The Pydantic code snippet to execute.
    Returns:
        Tuple[Dict[str, Any], Dict[str, type]]: A tuple containing the resulting
        variable dictionary and type dictionary.
    """
    if not code:
        raise exceptions.UnexpectedCaseException("Code snippet is empty.")

    # Define a dictionary to serve as the local namespace
    local_namespace = {"BaseModel": BaseModel}

    # Execute the code in the local namespace
    # TODO: do some sanity check on the code
    exec(code, local_namespace, local_namespace)

    result_var_dict = {}
    result_type_dict = {}
    for key, value in local_namespace.items():
        if key == "__builtins__":
            continue
        if key == "BaseModel":
            continue
        if isinstance(value, type):
            if issubclass(value, BaseModel):
                result_type_dict[key] = value
            else:
                logger().warning(f"Type {value} is not a subclass of BaseModel.")
            continue
        result_var_dict[key] = value

    return result_var_dict, result_type_dict
