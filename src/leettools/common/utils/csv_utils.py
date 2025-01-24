import csv
from typing import Any, Dict, List, Optional


def read_csv_to_dict_list(
    file_path: str, newline: Optional[str] = ""
) -> List[Dict[str, Any]]:
    """
    Read a CSV file into a list of dictionaries.

    Args:
    - file_path (str): The path to the CSV file.
    - newline (Optional[str]): The newline character. Default is "".

    Returns:
    - List[Dict[str, Any]]: The list of dictionaries. The keys are the column names.
    """
    with open(file_path, mode="r", encoding="utf-8", newline=newline) as csvfile:
        filtered_lines = (line for line in csvfile if not line.lstrip().startswith("#"))

        reader = csv.DictReader(filtered_lines)
        data = [row for row in reader]
    return data
