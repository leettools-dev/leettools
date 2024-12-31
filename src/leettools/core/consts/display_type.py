from enum import Enum


class DisplayType(str, Enum):
    """
    How the data is intended to be displayed. The detfault value is MD.

    If display is not MD, the user_data of the returned chat answer item will contain
    the data to be displayed.

    Right now the convention is:

    # WordCloud: the user_data should be
    #     Dict[str, Dict[str, int]]
    #     key: the word, the second key is the color/category, the value is the count

    # Table: the user_data should be
    #     header: List[str], rows: List[Dict[str, any]]
    #     the header is the column names,
    #     the rows is the list of the records
    #     each record is a dictionary with the column name as the key
    """

    MD = "MD"
    HTML = "HTML"
    TEXT = "TEXT"
    WORD_CLOUD = "WORD_CLOUD"
    SearchResultDocument = "SearchResultDocument"
    SearchResultSegment = "SearchResultSegment"
    IMAGE = "IMAGE"
    TABLE = "TABLE"
    CSV = "CSV"
    JSON = "JSON"
    REFERENCES = "REFERENCES"
