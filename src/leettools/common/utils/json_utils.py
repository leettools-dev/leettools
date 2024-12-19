import json
import re


def remove_trailing_commas(json_string: str) -> str:
    """Converts a JSON string into a well-formatted JSON without trailing commas."""
    # Parse the JSON string into a Python object
    parsed_json = json.loads(json_string)
    # Convert the Python object back to a JSON string
    formatted_json = json.dumps(parsed_json, indent=4)
    return formatted_json


def remove_json_block_marks(json_str: str) -> str:
    """Removes the leading and trailing block marks from a JSON string."""
    # Remove the leading and trailing block marks
    pattern = r"\n?```json\n?|\n?```\n?"
    response_str = re.sub(pattern, "", json_str)
    return response_str
