import threading
from abc import ABCMeta
from typing import Any, Dict


class SingletonMeta(ABCMeta):
    # todo: this masks the type of the class, may have a better solution
    _instances: Dict[str, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]
