from urllib.parse import urlparse

import requests
import tldextract

from leettools.common.logging import logger

DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
)


def normalize_url(url: str) -> str:
    """
    Normalizes the URL by removing the fragment and query.
    Also adding default https scheme if no scheme is provided.

    Args:
        url: The URL to be normalized.

    Returns:
        The normalized URL.
    """

    if "://" not in url:
        url = "https://" + url

    parsed_url = urlparse(url)

    parsed_url.geturl()

    # if no scheme is provided, add https
    if not parsed_url.scheme:
        parsed_url = parsed_url._replace(scheme="https")

    # Reconstruct the URL without the fragment and query
    parsed_url = parsed_url._replace(fragment="", query="")

    normalize_url = parsed_url.geturl()
    return normalize_url


def is_url_accessible(
    url: str, allow_redirects: bool = True, timeout: int = 5, user_agent: str = None
) -> bool:
    """
    Checks if a given URL is accessible by making an HTTP GET request.

    Args:
    -  url: The URL to check
    -  allow_redirects: Whether to allow redirects (default: True)
    -  timeout: The request timeout in seconds (default: 5)
    -  user_agent: The user agent to use in the request header (default: None)

    Returns:
    -  True if the URL is accessible, False otherwise
    """
    headers = {}

    # If a user agent is provided, use it, otherwise set a default user agent
    if user_agent:
        headers["User-Agent"] = user_agent
    else:
        headers["User-Agent"] = DEFAULT_USER_AGENT

    try:
        response = requests.get(
            url, timeout=timeout, allow_redirects=allow_redirects, headers=headers
        )
        # Return True if the status code is 200 (OK)
        if response.status_code == 200:
            return True
        else:
            logger().info(
                f"url {url} is not accessible, status code: {response.status_code}"
            )
            return False
    except requests.ConnectionError:
        # Handle connection errors (e.g., DNS issues, no internet, etc.)
        return False
    except requests.Timeout:
        # Handle request timeout
        return False
    except requests.RequestException:
        # Catch any other request-related exceptions
        return False


content_type_to_ext = {
    "md": "md",
    "markdown": "md",
    "text/markdown": "md",
    "text/html": "html",
    "text/plain": "txt",
    "text/css": "css",
    "text/javascript": "js",
    "application/javascript": "js",
    "application/json": "json",
    "application/xml": "xml",
    "application/xhtml+xml": "xhtml",
    "application/pdf": "pdf",
    "application/zip": "zip",
    "application/gzip": "gz",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/x-tar": "tar",
    "application/x-rar-compressed": "rar",
    "application/octet-stream": "bin",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "video/mp4": "mp4",
    "video/mpeg": "mpeg",
    "video/ogg": "ogv",
    "video/webm": "webm",
    "application/rtf": "rtf",
    "application/x-shockwave-flash": "swf",
    "application/vnd.android.package-archive": "apk",
    "application/x-7z-compressed": "7z",
    "application/x-bzip": "bz",
    "application/x-bzip2": "bz2",
    "application/x-cpio": "cpio",
    "application/x-deb": "deb",
    "application/x-iso9660-image": "iso",
    "application/x-lzh-compressed": "lzh",
    "application/x-msdownload": "exe",
    "application/x-rpm": "rpm",
    "application/x-sh": "sh",
    "application/x-tcl": "tcl",
    "application/x-tex": "tex",
    "application/x-apple-diskimage": "dmg",
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
}


def get_first_level_domain_from_url(url: str) -> str:
    """
    Get the first level domain from a URL.

    For example:

    url = 'https://www.example.com/path?query=param'
    domain = get_first_level_domain_from_url(url)

    domain == 'example'

    Args:
    - url (str): The URL to extract the first level domain from.

    Returns:
    - str: The first level domain extracted from the URL.
    """
    result = tldextract.extract(url)
    return result.domain


def get_domain_from_url(url: str) -> str:
    """
    Get the domain from a URL.

    For example:

    url = 'https://www.example.com/path?query=param'
    domain = get_domain_from_url(url)
    domain == 'www.example.com'

    url = "https://www.google.com"
    expected = "google.com"
    assert file_utils.get_domain_from_url(url) == expected

    url = "http://www.google.co.uk"
    expected = "google.co.uk"

    url = "http://test.setup.google.co.uk"
    expected = "google.co.uk"

    Args:
    - url (str): The URL to extract the domain from.

    Returns:
    - str: The domain extracted from the URL.
    """
    result = tldextract.extract(url)
    domain = ".".join([result.domain, result.suffix])
    return domain
