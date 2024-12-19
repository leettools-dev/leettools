from abc import ABC, abstractmethod
from typing import Any, ClassVar

from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_component_type import FlowComponentType


class AbstractIterator(ABC, FlowComponent):
    """
    An iterator is a flow component that iterates over a collection of items, usually
    documents or search results.
    """

    COMPONENT_TYPE = FlowComponentType.ITERATOR

    @staticmethod
    @abstractmethod
    def run(exec_info: ExecInfo, **kwargs) -> Any:
        pass
