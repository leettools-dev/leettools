from leettools.eds.scheduler.task.jobstore import AbstractJobStore, create_jobstore
from leettools.eds.scheduler.task.taskstore import AbstractTaskStore, create_taskstore
from leettools.settings import SystemSettings


class TaskManager:
    """
    The TaskManager is responsible for managing the taskstore and jobstore.
    """

    def __init__(self, settings: SystemSettings) -> None:
        self.taskstore = create_taskstore(settings)
        self.jobstore = create_jobstore(settings)

    def get_taskstore(self) -> AbstractTaskStore:
        return self.taskstore

    def get_jobstore(self) -> AbstractJobStore:
        return self.jobstore
