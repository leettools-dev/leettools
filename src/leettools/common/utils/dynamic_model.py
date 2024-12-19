from typing import Any, Dict, List, Optional, Type

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
