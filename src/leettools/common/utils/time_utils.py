from datetime import datetime


def cur_timestamp_in_ms() -> int:
    ct = datetime.now()
    timestamp_in_ms = int(ct.timestamp() * 1000)
    return timestamp_in_ms


def random_str(length: int = 8) -> str:
    import random
    import string

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
