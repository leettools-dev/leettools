from abc import ABC, abstractmethod
from typing import Any, ClassVar

from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_component_type import FlowComponentType


class AbstractSubflow(ABC, FlowComponent):
    """
    A subflow contains multiple steps. It is similar to a flow but there is no
    requirement to implement the execute_query method.
    """

    COMPONENT_TYPE = FlowComponentType.SUBFLOW

    @staticmethod
    @abstractmethod
    def run_subflow(exec_info: ExecInfo, **kwargs) -> Any:
        pass
