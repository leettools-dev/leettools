from pathlib import Path
from typing import Union

from leettools.common import exceptions


def generate_package_name(
    base_path: Union[str, Path], package_path: Union[str, Path]
) -> str:
    """
    Generate a Python package name based on relative path from the base project directory.

    Args:
    -   base_path: The base path of the Python project
    -   package_path: The path to the package

    Returns:
    -   A package-style name generated from the relative path

    Raises:
    -   ParametersValidationException: If the module path is not under the base project path
    """
    # Convert to Path objects for consistent handling
    base_path_obj: Path = Path(base_path).resolve()
    module_path_obj: Path = Path(package_path).resolve()

    # Ensure module_path is under base_path
    try:
        module_path_obj.relative_to(base_path_obj)
    except ValueError:
        raise exceptions.ParametersValidationException(
            [
                f"Module path {module_path_obj} must be under base project path {base_path_obj}"
            ]
        )

    # Generate relative path
    relative_path: Path = module_path_obj.relative_to(base_path_obj)

    # Convert path to package name
    package_parts: list[str] = list(relative_path.parts)

    # Remove file extension if it's a file
    if module_path_obj.is_file():
        package_parts[-1] = package_parts[-1].removesuffix(module_path_obj.suffix)

    # Convert to package name (dot-separated)
    package_name: str = ".".join(package_parts)

    return package_name


if __name__ == "__main__":
    BASE_PROJECT_PATH: Path = Path("/home/user/myproject/src")
    PACKAGE_PATH: Path = BASE_PROJECT_PATH / "leettools" / "common"

    result = generate_package_name(BASE_PROJECT_PATH, PACKAGE_PATH)
    if result:
        print(f"Generated package name: {result}")
