import pytest

from leettools.common.utils.csv_utils import read_csv_to_dict_list


@pytest.fixture
def sample_csv_file(tmp_path):
    data = """# This is a comment
name,age,city
Alice,30,New York
Bob,25,Los Angeles
# Another comment
Charlie,35,Chicago
"""
    file_path = tmp_path / "sample.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)
    return file_path


def test_read_csv_to_dict_list(sample_csv_file):
    expected_data = [
        {"name": "Alice", "age": "30", "city": "New York"},
        {"name": "Bob", "age": "25", "city": "Los Angeles"},
        {"name": "Charlie", "age": "35", "city": "Chicago"},
    ]

    result = read_csv_to_dict_list(sample_csv_file)
    assert result == expected_data


def test_read_csv_to_dict_list_with_newline(sample_csv_file):
    expected_data = [
        {"name": "Alice", "age": "30", "city": "New York"},
        {"name": "Bob", "age": "25", "city": "Los Angeles"},
        {"name": "Charlie", "age": "35", "city": "Chicago"},
    ]

    result = read_csv_to_dict_list(sample_csv_file, newline="\n")
    assert result == expected_data


def test_read_csv_to_dict_list_empty_file(tmp_path):
    file_path = tmp_path / "empty.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")

    result = read_csv_to_dict_list(file_path)
    assert result == []


def test_read_csv_to_dict_list_only_comments(tmp_path):
    data = """# This is a comment
# Another comment
"""
    file_path = tmp_path / "comments_only.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)

    result = read_csv_to_dict_list(file_path)
    assert result == []
