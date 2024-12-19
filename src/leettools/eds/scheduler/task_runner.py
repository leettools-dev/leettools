from abc import ABC, abstractmethod

from leettools.eds.scheduler.schemas.job import Job


class AbstractTaskRunner(ABC):

    @abstractmethod
    def run_job(self, job: Job) -> Job:
        """
        Run the task and update the job.

        Runner only updates the status of the job, it does not update the task.
        Scheudler is responsible for updating the task status because task maybe
        a recurring task.

        Args:
        - job: The job to run.

        Returns:
        - The job after running.
        """
        pass
