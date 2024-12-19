from abc import ABC, abstractmethod
from typing import Any, ClassVar

from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_component_type import FlowComponentType


class AbstractStep(ABC, FlowComponent):
    """
    A simple wrapper to provide a consistent interface for all steps in the flow.
    """

    COMPONENT_TYPE = FlowComponentType.STEP

    @staticmethod
    @abstractmethod
    def run_step(exec_info: ExecInfo, **kwargs) -> Any:
        pass
