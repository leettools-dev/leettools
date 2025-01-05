from datetime import datetime


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
