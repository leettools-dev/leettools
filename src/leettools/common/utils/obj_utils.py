import copy
from typing import Any, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel

from leettools.common import exceptions
from leettools.common.logging import logger

TypeVar_BaseModel = TypeVar("TypeVar_BaseModel", bound=BaseModel)

# DO NOT USE this prefix in field names
FIELD_NAME_PREFIX = "FIELD_"
ENV_VAR_PREFIX = "EDS_"


def add_env_var_constants(cls: TypeVar_BaseModel) -> TypeVar_BaseModel:
    """
    Decorator to add class-level field name constants for a Pydantic model.
    """
    for field_name in cls.model_fields.keys():
        # Add a class-level variable for each field name
        # TBD: maybe we want to check the alias property of the Field object
        env_var_name = f"{ENV_VAR_PREFIX}{field_name.upper()}"
        if env_var_name in cls.__dict__:
            raise exceptions.ParametersValidationException(
                [f"Field '{env_var_name}' already exists in the model object {cls}"]
            )
        setattr(cls, env_var_name, field_name)
    return cls


def add_fieldname_constants(cls: TypeVar_BaseModel) -> TypeVar_BaseModel:
    """
    Decorator to add class-level field name constants for a Pydantic model.
    """
    for field_name in cls.model_fields.keys():
        # Add a class-level variable for each field name
        # TBD: maybe we want to check the alias property of the Field object
        setattr(cls, f"{FIELD_NAME_PREFIX}{field_name.upper()}", field_name)
    return cls


def set_field_from_string(obj: BaseModel, field_name: str, value: str) -> None:
    """
    Set the value of a field in a Pydantic model from a string value. This function
    converts the string value to the appropriate type based on the field type in the model.

    Args:
    - obj (BaseModel): The Pydantic model object.
    - field_name (str): The name of the field to set.
    - value (str): The string value to set.

    Returns:
    - None
    """
    # Get the field type from the Pydantic model
    field_info = obj.model_fields.get(field_name)

    if field_info is None:
        raise exceptions.ParametersValidationException(
            [f"Field '{field_name}' not found in the model object {obj}"]
        )

    field_type = field_info.annotation  # Get the type of the field

    origin = get_origin(field_type)
    if origin is Union:
        # If the field type is a Union, get the first type in the Union
        # because typing.Optional[type] is a Union of the type and None
        args = get_args(field_type)
        field_type = args[0]
        if field_type is type(None):
            raise exceptions.ParametersValidationException(
                [f"Field '{field_name}' is not optional"]
            )
        if len(args) > 2:
            raise exceptions.ParametersValidationException(
                [f"Field '{field_name}' has more than 2 types: {args}"]
            )

    # Convert the string value to the appropriate type
    if field_type == bool:
        # Handle boolean conversion explicitly
        converted_value = value.lower() in ["true", "1", "yes"]
    else:
        try:
            converted_value = field_type(value)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Cannot convert value '{value}' to type {field_type}"
            ) from e

    # Set the field with the converted value
    setattr(obj, field_name, converted_value)


def assign_properties(source_obj: Any, dest_obj: Any, override: bool = False) -> None:
    """
    This function assigns the properties of the source object to the destination object.
    Useful for copying properties between two objects from the same base class.

    When override is set to False, it will NOT copy properties that has non-null default
    values in the destination object, since it is hard to differentiate a default value
    and a value that is set by the user.

    Args:
    - source_obj (Any): The source object from which to copy properties.
    - dest_obj (Any): The destination object to which to copy properties.
    - override (bool): Whether to override existing properties in the destination object.

    Returns:
    - None
    """
    for attr_name in dir(source_obj):
        if (
            attr_name in source_obj.__class_vars__
            or attr_name in dest_obj.__class_vars__
        ):
            continue

        if attr_name.startswith(FIELD_NAME_PREFIX):
            continue

        if not attr_name.startswith("_") and not callable(
            getattr(source_obj, attr_name)
        ):
            logger().noop(
                f"Checking attribute: {attr_name} from source to target",
                noop_lvl=3,
            )
            source_value = getattr(source_obj, attr_name)
            logger().noop(
                f"The source type is {type(source_value)}, value is {source_value}",
                noop_lvl=3,
            )
            if hasattr(dest_obj, attr_name):
                # runtime object type does not work. None value has type <NoneType>
                # so the type checking can only be done when the target has the attribute
                logger().noop(
                    f"The target attribute has type {type(getattr(dest_obj, attr_name))}",
                    noop_lvl=3,
                )
                if attr_name in dest_obj.__dict__:
                    dest_value = dest_obj.__dict__[attr_name]
                    if (
                        dest_value is None
                        or dest_value == ""
                        or dest_value == []
                        or dest_value == {}
                    ):
                        logger().noop(
                            f"The value of attribute: {attr_name} is None or empty, assigning",
                            noop_lvl=3,
                        )
                        target_value = copy.deepcopy(source_value)
                        setattr(dest_obj, attr_name, target_value)
                    else:
                        if override:
                            if isinstance(
                                source_value, type(getattr(dest_obj, attr_name))
                            ):
                                logger().noop(
                                    f"The value of attribute: {attr_name} is not None, overriding",
                                    noop_lvl=3,
                                )
                                target_value = copy.deepcopy(source_value)
                                setattr(dest_obj, attr_name, target_value)
                            else:
                                logger().noop(
                                    f"Target object has attribute: {attr_name} but the type is different",
                                    noop_lvl=3,
                                )
                        else:
                            # the value is already set and we don't want to override it
                            logger().noop(
                                f"The value of attribute: {attr_name} is not None, skipping",
                                noop_lvl=3,
                            )
                else:
                    logger().noop(
                        f"The attribute: {attr_name} does not exist in the target object, assigning",
                        noop_lvl=3,
                    )
                    target_value = copy.deepcopy(source_value)
                    if attr_name not in [
                        "model_computed_fields",
                        "model_config",
                        "model_extra",
                        "model_fields",
                        "model_fields_set",
                    ]:
                        setattr(dest_obj, attr_name, target_value)
            else:
                logger().noop(
                    f"Target object does not have attribute: {attr_name} skipping",
                    noop_lvl=3,
                )
    else:
        # the attribute is either internal or a function
        pass
