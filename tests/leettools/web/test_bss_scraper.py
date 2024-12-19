from pathlib import Path

from leettools.common.logging import logger
from leettools.context_manager import Context, ContextManager
from leettools.web.web_scraper import WebScraper


def test_bss_scraper():

    context = ContextManager().get_context()  # type: Context
    context.reset(is_test=True)

    display_logger = logger()

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
    )

    web_scrapper = WebScraper(
        context=context,
        user_agent=user_agent,
        scraper_type="beautiful_soup",
        display_logger=display_logger,
    )

    url = "https://www.example.com"

    results = web_scrapper.scrape_urls_to_file([url])
    assert len(results) == 1

    result = results[0]
    assert result.url == url
    assert result.file_path is not None
    assert Path(result.file_path).exists()

    old_file_path = result.file_path
    print(old_file_path)

    results = web_scrapper.scrape_urls_to_file([url])
    assert len(results) == 1
    result = results[0]
    assert result.url == url
    assert result.file_path == old_file_path
