# FlowType supported by the system
# should match subdir name in the flows directory
# custom flows can be referenced by module name directly

from enum import Enum


class FlowType(str, Enum):
    ANSWER = "answer"
    BOOTSTRAP = "bootstrap"
    EXTRACT = "extract"
    DIGEST = "digest"
    SEARCH = "search"
    NEWS = "news"
    OPINIONS = "opinions"
    MEDIUM = "medium"
    DUMMY = "dummy"  # mock the results for testing
