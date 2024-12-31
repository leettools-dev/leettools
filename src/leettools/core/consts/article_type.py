from enum import Enum


class ArticleType(str, Enum):
    """
    The article type, which defines the presentation of the final result.

    Each strategy type can only produce one type of article. Different strategy types
    may produce the same type of articles.
    """

    CHAT = "chat"  # an interactive chat interface
    NEWS = "news"  # a news article, usually just one section
    RESEARCH = "research"  # a multi-section research report
    SHOPPING = "shopping"  # a shopping list with links
    SEARCH = "search"  # a search result
    CSV = "csv"  # a CSV file
    JSON = "json"  # a JSON file
