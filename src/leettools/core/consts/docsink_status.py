from enum import Enum


class DocSinkStatus(str, Enum):
    CREATED = "Created"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
