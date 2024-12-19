# we can actually add a retriever only using LLM
# just ask LLM to return a list of links that match the query
from enum import Enum
from typing import List, Optional


class RetrieverType(str, Enum):
    BAIDU = "baidu"
    BING = "bing"
    LOCAL = "local"
    GOOGLE = "google"
    GOOGLE_PATENT = "google_patent"
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    SEARX = "searx"


def supported_retriever(region: Optional[str] = "all") -> List[str]:

    # we only show supported web retriever in the web UI
    if region is None:
        return [
            RetrieverType.GOOGLE.value,
            RetrieverType.GOOGLE_PATENT.value,
            RetrieverType.TAVILY.value,
            RetrieverType.BAIDU.value,
            RetrieverType.BING.value,
            RetrieverType.LOCAL.value,
        ]

    if region.lower() == "cn":
        return [
            RetrieverType.BAIDU.value,
            RetrieverType.BING.value,
            RetrieverType.LOCAL.value,
        ]

    if region.lower() == "us":
        return [
            RetrieverType.GOOGLE.value,
            RetrieverType.LOCAL.value,
        ]

    return [
        RetrieverType.GOOGLE.value,
        RetrieverType.LOCAL.value,
    ]
