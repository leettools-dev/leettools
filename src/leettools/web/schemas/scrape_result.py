from typing import Optional

from pydantic import BaseModel, Field

from leettools.core.consts.return_code import ReturnCode


class ScrapeResult(BaseModel):
    """
    Scrape result item from web scrapers.
    """

    url: str = Field(
        ...,
        description="The URL of the scraped page.",
    )
    file_path: Optional[str] = Field(
        None,
        description="The file path of the scraped page.",
    )
    content: Optional[str] = Field(
        None,
        description="The content of the scraped page.",
    )
    reused: Optional[bool] = Field(
        None,
        description="The flag indicating whether the content is reused.",
    )
    rtn_code: Optional[ReturnCode] = Field(
        None,
        description="The return code of the scraping job.",
    )
