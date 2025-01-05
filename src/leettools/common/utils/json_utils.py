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


def ensure_json_item_list(json_string: str) -> str:
    """
    Fixes an invalid JSON string by removing the last incomplete item from a list.
    Ensures that nested objects are retained correctly.

    Because some model may return trancated item lists.
    """
    # Trim whitespace and check for last bracket
    json_string = json_string.strip()

    pattern = r'^\s*\{\s*"items"\s*:\s*\[\s*'
    if not re.search(pattern, json_string):
        raise ValueError(
            "Invalid JSON string, expected to start with '{ \"items\": [', but got: "
            f"{json_string[:50]}"
        )

    # Attempt to parse progressively smaller portions of the JSON
    for i in range(len(json_string), 0, -1):
        try:
            fixed_json = json.loads(
                json_string[:i] + "]}"
            )  # Try to close JSON properly
            return json.dumps(fixed_json, indent=2)  # Return formatted valid JSON
        except json.JSONDecodeError:
            continue  # Keep trying with a smaller substring

    raise ValueError(f"Unable to fix JSON string, no valid JSON found: {json_string}")
