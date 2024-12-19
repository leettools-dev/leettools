from enum import Enum


class DocumentStatus(str, Enum):
    CREATED = "Created"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
