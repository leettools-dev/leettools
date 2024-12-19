from enum import Enum


class StrategySectionName(str, Enum):
    """
    The name of predefined strategy sections, basically the category of flow steps
    we support. Each section can be considered as a building block for a sequence of
    flow steps.
    """

    WEBSEARCH = "websearch"
    INTENTION = "intention"
    REWRITE = "rewrite"
    SEARCH = "search"
    RERANK = "rerank"
    CONTEXT = "context"
    INFERENCE = "inference"
    SUMMARY_DOCUMENT = "summary_document"
    PLAN_SECTION = "plan_section"
    GENERAL = "general"
