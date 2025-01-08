from leettools.common.utils.time_utils import parse_date


def test_parse_date():
    test_dates = ["2024-01-08", "2024/01/08", "01-08-2024", "01/08/2024"]

    for date in test_dates:
        parsed_date = parse_date(date)
        print(f"Original: {date} -> Parsed: {parsed_date}")
        assert parsed_date is not None
        assert parsed_date.year == 2024
        assert parsed_date.month == 1
        assert parsed_date.day == 8

    try:
        first_date = parse_date("2024-01-08")
        second_date = parse_date("2024-01-09")
        test_date_max = max(first_date, second_date)
        assert test_date_max == second_date
        max(first_date, None)
        assert False
    except TypeError:
        assert True

    output_date = parse_date("2024/01/08")
    output_date_str = str(output_date.date())
    print(f"Output date: {output_date_str}")
    assert output_date_str == "2024-01-08"
