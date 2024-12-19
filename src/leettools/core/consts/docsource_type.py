from enum import Enum


class DocSourceType(str, Enum):
    FILE = "file"  # uploaded file
    NOTION = "notion"  # notion integration
    URL = "url"  # single URL
    LOCAL = "local"  # local directory or file
    WEB = "website"  # web site
    SEARCH = "search"  # search engine
    IMG = "image"  # image
    VID = "video"  # video
    AUDIO = "audio"  # audio
