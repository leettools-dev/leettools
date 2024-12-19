from typing import ClassVar, Optional

from pydantic import BaseModel

from leettools.common import exceptions
from leettools.common.utils import obj_utils


class PerfBaseModel(BaseModel):
    """
    Base class for performance related configuration.
    """

    @classmethod
    def from_base_model(cls, base_model_obj: BaseModel) -> "PerfBaseModel":
        """
        Get all fields from the base model object and create a new config object.
        """
        obj = cls()
        obj_utils.assign_properties(base_model_obj, obj, override=True)
        return obj


class PerformanceConfigurable:
    """
    Any class that has configuration that may affect the retrieval peformance should
    inherit from this class. It provides the interface to set and get the performance
    related configuration.
    """

    # has to be set by the child class
    PerfConfigIdStr: ClassVar[str] = None

    @classmethod
    def record_perf_config(cls, perf_config: PerfBaseModel) -> None:
        """
        Record the performance related config. This function only works in the non-svc
        environment for now. In a svc environment, each component runs separately and
        recording an end-to-end performance config does not make sense.
        """
        if cls.PerfConfigIdStr is None:
            raise exceptions.UnexpectedCaseException(
                "PerfConfigIdStr has not been set for the class."
            )

        from leettools.context_manager import ContextManager

        context = ContextManager().get_context()
        if context.is_svc:
            return

        config_manager = context.get_config_manager()

        config_manager.add_config(cls.PerfConfigIdStr, perf_config)

    @classmethod
    def get_perf_config(cls) -> Optional[BaseModel]:
        """
        Get the performance related config.
        """
        if cls.PerfConfigIdStr is None:
            raise exceptions.UnexpectedCaseException(
                "PerfConfigIdStr has not been set for the class."
            )

        from leettools.context_manager import ContextManager

        context = ContextManager().get_context()
        if context.is_svc:
            raise exceptions.UnexpectedCaseException(
                "Trying to read perf config in svc context."
            )

        config_manager = context.get_config_manager()

        return config_manager.get_config(cls.PerfConfigIdStr, None)
