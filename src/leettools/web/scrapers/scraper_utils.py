from datetime import datetime, timedelta

from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import file_utils, time_utils
from leettools.core.consts.return_code import ReturnCode
from leettools.web.schemas.scrape_result import ScrapeResult


def check_existing_file(
    url: str, dir: str, filename_prefix: str, suffix: str, display_logger: EventLogger
) -> ScrapeResult:
    existing_file_list = file_utils.get_files_with_timestamp(
        dir, filename_prefix, suffix
    )
    if existing_file_list:
        latest_file, ts = existing_file_list[0]
        display_logger.debug(
            f"File with the same name and suffix already exists: {latest_file}, "
            f"timestamp: {ts}"
        )
        # if the latest file is less than 1 day old, skip the scraping
        now = time_utils.current_datetime()
        diff: timedelta = now - ts
        # TODO: make the delta configurable
        if diff.days < 1:
            display_logger.debug(
                f"Skipping saving: {url}: file already exists and is less than 1 day old"
            )
            file_path = f"{dir}/{latest_file}"
            # TODO: maybe we can check the content length here
            return ScrapeResult(
                url=url,
                file_path=file_path,
                content=None,
                reused=True,
                rtn_code=ReturnCode.SUCCESS,
            )
        else:
            display_logger.debug(f"File is older than 1 day, scraping again: {url}")
            return None
    else:
        return None


def is_content_length_ok(content: str, display_logger: EventLogger) -> bool:
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    if context.is_test:
        display_logger.info(f"In the test mode. Ignoring the content length check.")
    else:
        if len(content) < 300:
            display_logger.info(
                f"Content length is too short: {len(content)} characters"
            )
            display_logger.info(f"Short content: {content}")
            return False
    return True
