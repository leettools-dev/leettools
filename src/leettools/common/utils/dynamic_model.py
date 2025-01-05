from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, create_model

from leettools.common.utils.obj_utils import TypeVar_BaseModel


def _convert_type(type: Any, models: Dict[str, Type[TypeVar_BaseModel]] = {}) -> Type:
    try:
        return eval(
            type,
            None,
            {
                "array": list,
                "number": float,
                "integer": int,
                "string": str,
                "List": List,
                "Dict": Dict,
                "Any": Any,
                **models,
            },
        )
    except NameError:
        raise ValueError(f"Unsupported type: {type}")


def create_pydantic_model(
    model_name: str,
    schema_dict: Dict[str, Any],
    models: Dict[str, Type[TypeVar_BaseModel]] = {},
) -> type[BaseModel]:
    """
    Create a dynamic pydantic model from a schema dict.

    Args:
    - model_name: The name of the model.
    - schema_dict: The schema dict.
    - models: The models to be used in the schema dict.

    Returns:
    - The new model.
    """
    fields = {
        field_name: (Optional[_convert_type(field_type, models)], None)
        for field_name, field_type in schema_dict.items()
    }
    model = create_model(model_name, **fields)
    return model


def gen_pydantic_example(
    model_cls: Type[TypeVar_BaseModel], show_type: bool
) -> Dict[str, Any]:
    """
    Generates example JSON data from a Pydantic model.
    Handles all field types including nested models, lists, dictionaries, and optionals.

    Args:
    - model_cls: The Pydantic model class.
    - show_type: Show the type in the example, use example value if False.

    Returns:
    - Dict[str, Any]: Example JSON data
    """
    example = {}

    for field_name, field_info in model_cls.model_fields.items():
        field_type = field_info.annotation

        example[field_name] = _get_example_value(field_type, show_type)

    return example


def _get_example_value(field_type: Any, show_type: bool) -> Any:
    """
    Returns an example value based on the field type.
    Recursively handles nested models, lists, and dictionaries.
    """
    if hasattr(
        field_type, "__origin__"
    ):  # Handles generics (List, Dict, Optional, Union)
        if field_type.__origin__ is list and field_type.__args__:
            return [
                _get_example_value(field_type.__args__[0], show_type)
            ]  # Example list with one item
        elif field_type.__origin__ is dict and len(field_type.__args__) == 2:
            return {
                "key": _get_example_value(field_type.__args__[1], show_type)
            }  # Example dict
        elif field_type.__origin__ is Union and type(None) in field_type.__args__:
            return _get_example_value(
                field_type.__args__[0], show_type
            )  # Handle Optional[X] as X

    elif _issubclass_safe(field_type, BaseModel):  # Handles nested Pydantic models
        return gen_pydantic_example(field_type, show_type)

    # Default example values based on primitive types
    if show_type:
        example_values = {
            int: "int",
            float: "float",
            str: "str",
            bool: "bool",
            datetime: "datetime",
        }
    else:
        example_values = {
            int: 42,
            float: 3.14,
            str: "example",
            bool: True,
            datetime: "2025-01-01T00:00:00Z",
        }

    return example_values.get(field_type, None)  # Default to None for unsupported types


def _issubclass_safe(cls, base):
    """Safe issubclass check to avoid errors with non-class types"""
    try:
        return issubclass(cls, base)
    except TypeError:
        return False
