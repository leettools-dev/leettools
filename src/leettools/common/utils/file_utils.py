import glob
import hashlib
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import url2pathname

from leettools.common import exceptions
from leettools.common.exceptions import UnexpectedCaseException, UnexpectedIOException
from leettools.common.utils import time_utils

# Define a dictionary for other replacements
replacements = {
    "#": "_",
    "$": "_",
    "&": "and",
    "'": "",
    "(": "",
    ")": "",
    "*": "_",
    "+": "_",
    ",": "_",
    "/": "_",
    ":": "_",
    ";": "_",
    "=": "_",
    "?": "_",
    "@": "_",
    "[": "",
    "]": "",
    '"': "",
    "<": "_",
    ">": "_",
    "\\": "_",
    "^": "_",
    "{": "",
    "|": "_",
    "}": "",
    "~": "_",
    "`": "_",
}


def create_symlink(src_filename: str, dest_filename: str) -> None:
    """
    Create a symbolic link from the source file to the destination file.

    Args:
        src (str): The source file.
        dest (str)): The destination file.
    """

    src = Path(src_filename)

    if not src.exists():
        raise exceptions.CopyFileException(
            error_msg=(
                f"creating a symlink from {src_filename} to {dest_filename}. "
                "The source file does not exist."
            )
        )

    dest = Path(dest_filename)
    if dest.exists():
        if os.path.islink(dest):
            os.unlink(dest)
        else:
            raise exceptions.CopyFileException(
                error_msg=(
                    f"creating a symlink from {src} to {dest}. "
                    "The destination file already exists and is not a symlink."
                )
            )

    # Create a symbolic link from the source to the destination
    os.symlink(src, dest)


def redact_api_key(api_key: str) -> str:
    """
    Redact an API key by replacing all but the last 4 characters with asterisks.

    Args:
    - api_key (str): The API key to redact.

    Returns:
    - str: The redacted API key.
    """
    asterisks = "******"
    if len(api_key) <= 6:
        return f"{api_key[0]}{asterisks}"
    if len(api_key) < 12:
        return f"{api_key[:3]}{asterisks}{api_key[-3:]}"
    return f"{api_key[:5]}{asterisks}{api_key[-5:]}"


def is_valid_filename(filename: str) -> bool:
    try:
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Try to create a temporary file with the given filename in the temporary directory
            tmpfile_path = os.path.join(tmpdirname, filename)
            with open(tmpfile_path, "w", encoding="utf-8") as tmpfile:
                tmpfile.write("test")
            with open(tmpfile_path, "r", encoding="utf-8") as tmpfile:
                read_content = tmpfile.read()
                if read_content != "test":
                    return False
        return True
    except OSError:
        return False


def parse_uri_for_search_params(uri: str) -> Dict[str, str]:
    # Define the keys that are expected in the URI
    expected_keys = {"q", "date_range", "max_results", "ts"}
    # Parse the URI
    parsed_uri = urlparse(uri)

    # Check if the scheme and netloc (provider) is correct
    if parsed_uri.scheme != "search":
        raise UnexpectedCaseException(f"Unsupported URI scheme: {parsed_uri.scheme}")

    provider = parsed_uri.netloc

    # Extract the query parameters
    query_params = parse_qs(parsed_uri.query)

    # Initialize the dictionary with None for all expected parameters
    params_dict = {key: None for key in expected_keys}

    params_dict["provider"] = provider

    # Update the dictionary with values from the URI
    for key in query_params:
        params_dict[key] = query_params[key][0] if query_params[key] else None

    # Add any unknown parameters to the dictionary
    for key in query_params:
        if key not in params_dict:
            params_dict[key] = query_params[key][0] if query_params[key] else None

    return params_dict


def file_hash_and_size(file_path: Path) -> Tuple[str, int]:
    """
    Calculate the SHA256 hash and size of a file.

    Args:
        file_path (Path): The path to the file.

    Returns:
        Tuple[str, int]: A tuple containing the file hash (SHA256) and size.

    Raises:
        UnexpectedIOException: If an unexpected error occurs while hashing the file.

    """
    try:
        with open(file_path, "rb") as file:
            file_content = file.read()
            file_size = len(file_content)
            file_hash = hashlib.sha256(file_content).hexdigest()
            return file_hash, file_size
    except Exception as e:
        raise UnexpectedIOException(
            operation_desc=f"hashing the file {file_path}", exception=e
        )


def get_absolute_path(path_str: str) -> Path:
    """
    Get the absolute path of a file or directory.

    Args:
        path_str (str): The path of the file or directory.

    Returns:
        Path: The absolute path of the file or directory.
    """
    path = Path(path_str)
    return path.resolve()


def readable_timestamp() -> str:
    """
    Get the current datetime and transform it into a string format.

    Returns:
        Formatted datetime string ('YYYY-MM-DD HH:MM:SS')
    """
    now = time_utils.current_datetime()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    return timestamp


def filename_timestamp(now: Optional[datetime] = None) -> str:
    """
    Get the current datetime and transform it into a string format.

    Args:
    -   now (Optional[datetime]): The datetime object to use for the timestamp.

    Returns:
    -   Formatted datetime string ("%Y-%m-%d-%H-%M-%S-%f")
    """
    if now is None:
        now = time_utils.current_datetime()
    # generate a timestamp up to milliseconds that can be used in a filename
    timestamp = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
    return timestamp


def filename_timestamp_to_datetime(timestamp: str) -> datetime:
    """
    Convert a timestamp string to a datetime object.

    Args:
        timestamp (str): The timestamp string ("%Y-%m-%d-%H-%M-%S-%f")

    Returns:
        datetime: The datetime object.
    """
    return datetime.strptime(timestamp, "%Y-%m-%d-%H-%M-%S-%f")


def get_files_with_timestamp(
    directory: str, prefix: str, suffix: str
) -> List[Tuple[str, datetime]]:
    """
    Finds files with a given prefix and suffix, with the middle part matching a
    timestamp in "%Y-%m-%d-%H-%M-%S-%f" format.

    Args:
    - directory (str): The directory to search in.
    - prefix (str): The prefix of the filename.
    - suffix (str): The suffix of the filename.

    Returns:
    - A list of tuples, where each tuple contains the filename and the timestamp parts.

    """
    # Define a regex pattern for the timestamp (YYYY-MM-DD-HH-MM-SS-ffffff)
    timestamp_regex = r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{6})"
    # print(f"\ntimestamp_regex is {timestamp_regex}")

    # Create a pattern that combines prefix, timestamp, and suffix
    pattern = f"{prefix}*{suffix}"

    # Construct the full search path
    search_path = os.path.join(directory, pattern)
    # print(f"search_path is {search_path}")

    # Use glob to find files matching the pattern
    matching_files = glob.glob(search_path)

    results = []

    # Build the full regex with the prefix and suffix
    full_regex_pattern = (
        re.escape(prefix + ".") + timestamp_regex + re.escape("." + suffix)
    )
    # print(f"full_regex_pattern is {full_regex_pattern}")

    for file in matching_files:
        filename = os.path.basename(file)
        # print(f"filename is {filename}")

        # Extract the parts of the filename that matched the timestamp pattern
        match = re.match(full_regex_pattern, filename)

        if match:
            timestamp_parts = match.groups()[0]
            # print(f"timestamp_parts is {timestamp_parts}")
            timestamp = filename_timestamp_to_datetime(timestamp_parts)
            results.append((filename, timestamp))

    # sort the results by timestamp
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def read_template_file(file_path: str) -> str:
    """
    Read a template file and return its content as a string, ignoring lines started with #.

    Args:
        file_path (str): The path of the file to read.

    Returns:
        str: The content of the file.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        content = []
        for line in file:
            # Strip whitespace from the beginning and end of the line
            stripped_line = line.strip()
            # Check if the line is not empty and does not start with '#'
            if stripped_line and not stripped_line.startswith("#"):
                content.append(stripped_line)

    # Join the content list into a single string, if needed
    content_str = "\n".join(content)
    return content_str


def uri_to_path(uri: str) -> Path:
    """
    Convert a URI to a file path.
    """
    result = urlparse(uri)
    file_path = url2pathname(result.path)
    return Path(file_path)


def extract_filename_from_uri(uri: str) -> str:
    """
    Extract the filename from a URI. Basically the basename of the URI path part.

    If the basename is longer than 128 characters, it is truncated to 128 characters.

    If the URI ends with a slash or the basename is empty, the filename is set to "index".

    Args:
    - uri (str): The URI to extract the filename from.

    Returns:
    - str: The extracted filename.
    """
    parsed_uri = urlparse(uri)
    basename = os.path.basename(parsed_uri.path)
    if len(basename) > 128:
        basename = basename[:128]
    if uri.endswith("/") or basename == "":
        basename = "index"
    return sanitize_file_name(basename)


def extract_file_suffix_from_url(uri: str) -> str:
    """
    Return the file suffix of a URL.

    If the URL ends with a slash or the basename is empty, the suffix is set to "html".

    Args:
    - uri (str): The URL to extract the file suffix from.

    Returns:
    - str: The file suffix. "" if no suffix is found.
    """

    # Parse the URL to extract the path
    parsed_uri = urlparse(uri)
    # Get the path from the URL
    path = parsed_uri.path
    basename = os.path.basename(path)

    if uri.endswith("/") or basename == "":
        file_suffix = "html"
    else:
        # Extract the file extension (suffix) using os.path.splitext
        _, file_suffix = os.path.splitext(path)

    # Return the suffix without the leading dot, or an empty string if no suffix
    return file_suffix.lstrip(".") if file_suffix else ""


def sanitize_file_name(file_name: str) -> str:
    # Decode any percent-encoded characters
    file_name = unquote(file_name)
    # Replace spaces with underscores
    file_name = file_name.replace(" ", "_")

    # Replace each problematic character
    for char, replacement in replacements.items():
        file_name = file_name.replace(char, replacement)

    # Remove any non-ASCII characters
    file_name = "".join(c for c in file_name if ord(c) < 128)

    return file_name


def get_base_domain(url: str) -> str:
    # Extract the domain from the URL
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    # Split the domain into parts
    parts = domain.split(".")

    # Return the base domain (last two parts), e.g., 'yahoo.com'
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def is_subdomain_or_same(base_url: str, check_url: str) -> bool:
    """
    Check if the check URL is a subdomain of the base URL or the same domain.

    print(is_subdomain_or_same("http://yahoo.com", "http://news.yahoo.com"))   # True
    print(is_subdomain_or_same("http://yahoo.com", "http://yahoo.com/news"))   # True
    print(is_subdomain_or_same("http://yahoo.com", "http://yahoo.co.jp"))      # False

    Args:

        base_url (str): The base URL.
        check_url (str): The URL to check.

    Returns:
        bool: True if check_url is a subdomain of the base_urlor the same domain, False otherwise.
    """
    base_domain = get_base_domain(base_url)
    check_domain = get_base_domain(check_url)

    # Ensure that both domains are the same (ignoring subdomains)
    return base_domain == check_domain
