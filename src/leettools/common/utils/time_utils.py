from datetime import datetime
from typing import Optional

from dateutil import parser


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parses a date string into a datetime object, automatically handling different formats.

    Supported formats:
    - yyyy-mm-dd
    - yyyy/mm/dd
    - mm-dd-yyyy
    - mm/dd/yyyy

    Args:
    - date_str (str): The input date string.

    Returns:
    - Optional[datetime]: A datetime object if parsing succeeds, else None.

    Example:
        >>> parse_date("2024-01-08")
        datetime.datetime(2024, 1, 8, 0, 0)
        >>> parse_date("01/08/2024")
        datetime.datetime(2024, 1, 8, 0, 0)
    """
    try:
        # Use dateutil's parser for flexible date parsing
        dt = parser.parse(date_str, dayfirst=False, yearfirst=True)
        return dt
    except Exception:
        return None  # Return None if parsing fails


def current_datetime() -> datetime:
    return datetime.now()


def cur_timestamp_in_ms() -> int:
    ct = datetime.now()
    timestamp_in_ms = int(ct.timestamp() * 1000)
    return timestamp_in_ms


def enforce_timezone(dt: datetime) -> datetime:
    new_dt = dt.replace(tzinfo=None)
    return new_dt


def datetime_from_timestamp_in_ms(timestamp_in_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_in_ms / 1000)


def random_str(length: int = 8) -> str:
    import random
    import string

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
