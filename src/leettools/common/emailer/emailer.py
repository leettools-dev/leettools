from abc import ABC, abstractmethod

from leettools.settings import SystemSettings


class AbstractEmailer(ABC):
    @abstractmethod
    def __init__(self, settings: SystemSettings) -> None:
        pass

    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> None:
        pass


def create_emailer(settings: SystemSettings) -> AbstractEmailer:
    import os

    from leettools.common.utils import factory_util

    module_name = os.environ.get(SystemSettings.EDS_DEFAULT_EMAILER)
    if module_name is None or module_name == "":
        module_name = settings.DEFAULT_EMAILER

    if "." not in module_name:
        module_name = f"{__package__}._impl.{module_name}"

    return factory_util.create_object(
        module_name,
        AbstractEmailer,
        settings=settings,
    )
