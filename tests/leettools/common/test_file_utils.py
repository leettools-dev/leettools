from datetime import datetime

import leettools.common.utils.url_utils
from leettools.common.utils import file_utils, time_utils


def test_parse_uri_for_search_params():
    uri = "search://?q=test&date_range=2022-01-01&max_results=10&ts=2022-01-01"
    expected = {
        "q": "test",
        "date_range": "2022-01-01",
        "max_results": "10",
        "ts": "2022-01-01",
        "provider": "",
    }
    assert file_utils.parse_uri_for_search_params(uri) == expected


def test_redact_api():

    asterisks = "******"
    api_key = "12345abcdedfabcdedfabcdedfabcdedfabcdedf67890"
    expected = f"12345{asterisks}67890"
    assert file_utils.redact_api_key(api_key) == expected

    api_key = "12345"
    expected = f"1{asterisks}"
    assert file_utils.redact_api_key(api_key) == expected

    api_key = "1234567890"
    expected = f"123{asterisks}890"
    assert file_utils.redact_api_key(api_key) == expected


def test_is_valid_filename():
    filename = "test.txt"
    assert file_utils.is_valid_filename(filename) == True

    filename = "test/./test[].txt"
    assert file_utils.is_valid_filename(filename) == False


def test_get_first_level_domain_from_url():
    url = "https://www.google.com"
    expected = "google"
    assert (
        leettools.common.utils.url_utils.get_first_level_domain_from_url(url)
        == expected
    )

    url = "http://www.google.co.uk"
    expected = "google"
    assert (
        leettools.common.utils.url_utils.get_first_level_domain_from_url(url)
        == expected
    )

    url = "http://test.setup.google.co.uk"
    excepted = "google"
    assert (
        leettools.common.utils.url_utils.get_first_level_domain_from_url(url)
        == expected
    )


def test_get_domain_from_url():

    url = "https://www.google.com"
    expected = "google.com"
    assert leettools.common.utils.url_utils.get_domain_from_url(url) == expected

    url = "http://www.google.co.uk"
    expected = "google.co.uk"
    assert leettools.common.utils.url_utils.get_domain_from_url(url) == expected

    url = "http://test.setup.google.co.uk"
    expected = "google.co.uk"
    assert leettools.common.utils.url_utils.get_domain_from_url(url) == expected


def test_filename_timestamp_to_datetime():
    now = time_utils.current_datetime()

    filename_timestamp = file_utils.filename_timestamp(now)

    now_back = file_utils.filename_timestamp_to_datetime(filename_timestamp)

    assert now == now_back


def test_get_files_with_timestamp(tmp_path):

    prefix = "test"
    suffix = "txt"

    ts_O1 = time_utils.current_datetime()
    timestamp_01 = file_utils.filename_timestamp(now=ts_O1)
    file_path_01 = f"{tmp_path}/{prefix}.{timestamp_01}.{suffix}"
    with open(file_path_01, "w") as file:
        file.write("test1")

    file_list = file_utils.get_files_with_timestamp(tmp_path, prefix, suffix)
    assert len(file_list) == 1

    file_name, ts_01_read = file_list[0]
    assert file_name == f"{prefix}.{timestamp_01}.{suffix}"
    assert ts_O1 == ts_01_read

    ts_O2 = time_utils.current_datetime()
    timestamp_02 = file_utils.filename_timestamp(now=ts_O2)
    file_path_02 = f"{tmp_path}/{prefix}.{timestamp_02}.{suffix}"
    with open(file_path_02, "w") as file:
        file.write("test2")

    file_list = file_utils.get_files_with_timestamp(tmp_path, prefix, suffix)
    assert len(file_list) == 2

    file_name, ts_02_read = file_list[0]
    assert file_name == f"{prefix}.{timestamp_02}.{suffix}"
    assert ts_O2 == ts_02_read


def test_extract_file_suffix_from_url() -> None:

    url1 = "https://example.com/path/to/file.txt"
    assert file_utils.extract_file_suffix_from_url(url1) == "txt"

    url2 = "https://example.com/path/to/file"
    assert file_utils.extract_file_suffix_from_url(url2) == ""

    url3 = "https://example.com/path/to/file."
    assert file_utils.extract_file_suffix_from_url(url3) == ""

    url4 = "https://example.com/path/to/file.txt?query=1"
    assert file_utils.extract_file_suffix_from_url(url4) == "txt"

    url5 = "https://example.com/path/to/"
    assert file_utils.extract_file_suffix_from_url(url5) == "html"

    url6 = "https://example.com/path/to"
    assert file_utils.extract_file_suffix_from_url(url6) == ""
