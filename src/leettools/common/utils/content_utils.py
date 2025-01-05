import re
from typing import Optional


def is_meaningful(content: str) -> bool:
    """
    The content is not meaningful if it is:
    1. None
    2. less than 100 characters
    3. contains only warning messages

    Args:
    content (str): The content to check.

    Returns:
    bool: True if the content is meaningful, False otherwise.
    """
    if content is None:
        return False
    if len(content) < 100:
        return False
    return True


def get_image_url(content: str) -> Optional[str]:
    # Regular expression to find markdown links that point to images
    image_link_pattern = r"\[.*?\]\((.*?\.(?:png|jpg|jpeg|gif|bmp|tiff|webp|svg))\)"

    # Search for the first matching image link in the markdown content
    match = re.search(image_link_pattern, content, re.IGNORECASE)

    if match:
        return match.group(1)  # Return the first captured group (the image link)
    else:
        return None  # Return None if no image link is found


def normalize_newlines(text: str) -> str:
    """
    Normalize newlines in the given text.
    """
    return re.sub(r"\s*\n\s*", "\n", text).strip()


def truncate_str(s: str, x: int) -> str:
    """
    Truncate the string to a maximum length of x characters.

    If the string is longer than x characters, the middle part is replaced with "[... omitted ...]".

    Args:
    - s (str): The string to truncate.
    - x (int): The maximum length of the truncated string.

    Returns:
    - str: The truncated string.
    """
    stuff = "[... omitted ...]"

    if len(s) <= x:
        return s  # Return original string if within limit

    # Calculate split lengths
    prefix_len = int(0.8 * x)  # First 80% of the string
    suffix_len = x - (prefix_len + len(stuff))  # Remaining after inserting marker

    if suffix_len <= 0:
        suffix_len = 0  # Ensure non-negative suffix length

    return s[:prefix_len] + stuff + s[-suffix_len:]
