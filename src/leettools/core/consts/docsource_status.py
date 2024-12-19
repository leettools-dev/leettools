from enum import Enum


class DocSourceStatus(str, Enum):
    CREATED = "Created"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ABORTED = "Aborted"
    PARTIAL = "Partial"
