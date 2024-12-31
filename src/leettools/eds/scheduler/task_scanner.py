from abc import ABC, abstractmethod
from typing import List, Optional

from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.eds.scheduler.schemas.task import Task


class AbstractTaskScanner(ABC):

    @abstractmethod
    def scan_kb_for_tasks(
        self,
        target_org: Optional[Org] = None,
        target_kb: Optional[KnowledgeBase] = None,
        target_docsources: Optional[List[DocSource]] = None,
    ) -> List[Task]:
        """
        Scan the database for tasks.

        Args:
        - target_org: The organization to scan, if None, scan all organizations.
        - target_kb: The knowledgebase to scan, if None, scan all knowledgebases in the org.
        - target_docsources: The docsource to scan, if None, scan all docsources in the kb.

        Returns:
        - The tasks that need to run.
        """
        pass
