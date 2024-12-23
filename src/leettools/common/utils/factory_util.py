import importlib
import inspect
from abc import ABC
from typing import Type, TypeVar

from leettools.common import exceptions
from leettools.common.logging import logger

T = TypeVar("T", bound=ABC)


def get_subclass_from_module(module_name: str, base_class: Type[T]) -> Type[T]:
    # Ensure the base_class is a subclass of ABC
    if not issubclass(base_class, ABC):
        raise exceptions.InvalidValueException(
            name="base_class",
            expected="subclass of ABC",
            actual=base_class.__name__,
        )

    try:
        # Import the specified module
        module = importlib.import_module(module_name)

        # Find all classes in the module that are a subclass of the specified base class
        subclasses = [
            cls
            for _, cls in inspect.getmembers(module, inspect.isclass)
            if issubclass(cls, base_class) and cls is not base_class
        ]

        if len(subclasses) == 0:
            raise exceptions.UnexpectedCaseException(
                f"No subclasses of {base_class} found in the module {module_name}."
            )
        elif len(subclasses) > 1:
            raise exceptions.UnexpectedCaseException(
                f"More than one subclass of {base_class} found in the module {module_name}."
            )

        # Return an instance of the found class
        cls = subclasses[0]
        return cls
    except ModuleNotFoundError as e:
        raise exceptions.EntityNotFoundException(
            entity_name=module_name, entity_type="module"
        )


def create_object(module_name: str, base_class: Type[T], *args, **kwwargs) -> T:
    cls = get_subclass_from_module(module_name, base_class)
    return cls(*args, **kwwargs)


def create_manager_with_repo_type(
    manager_name: str, repo_type: str, base_class: Type[T], *args, **kwwargs
) -> T:
    """
    Dynamically creates and returns an instance of a manager class based on the given
    repository type. This function constructs the module name for the manager class
    using the provided `manager_name` and `repo_type`. It then imports the module and
    creates an instance of the manager class, ensuring it is a subclass of `base_class`.

    Args:
    -    manager_name (str): The name of the manager.
    -    repo_type (str): The type of the repository.
    -    base_class (Type[T]): The base class that the manager class should inherit from.
    -    *args: Additional positional arguments to pass to the manager class constructor.
    -    **kwwargs: Additional keyword arguments to pass to the manager class constructor.
    Returns:
    -    T: An instance of the manager class.
    """
    import os

    module_name = os.environ.get(f"EDS_{manager_name.upper()}")
    if module_name is None or module_name == "":
        module_name = f"{manager_name}_{repo_type}"

    if "." not in module_name:
        # remove the last part of the module name
        package = ".".join(base_class.__module__.split(".")[:-1])
        full_module_name = f"{package}._impl.{repo_type}.{module_name}"
    else:
        full_module_name = module_name

    logger().debug(
        f"Creating manager object with name {manager_name}, repo type {repo_type}, "
        f"and module name {full_module_name}"
    )

    return create_object(
        full_module_name,
        base_class,
        *args,
        **kwwargs,
    )
