# FlowType supported by the system
# should match subdir name in the flows directory
# custom flows can be referenced by module name directly

from enum import Enum


class FlowType(str, Enum):
    ANSWER = "answer"
    BOOTSTRAP = "bootstrap"
    EXTRACTOR = "extractor"
    DIGEST = "digest"
    SEARCH = "search"
    NEWS = "news"
    OPINIONS = "opinions"
    DUMMY = "dummy"  # mock the results for testing
