from abc import ABC, abstractmethod
from typing import List

from leettools.eds.scheduler.schemas.task import Task


class AbstractTaskScanner(ABC):

    @abstractmethod
    def scan_kb_for_tasks(self) -> List[Task]:
        """
        Scan the database for tasks.

        Returns:
        - The tasks that need to run.
        """
        pass
