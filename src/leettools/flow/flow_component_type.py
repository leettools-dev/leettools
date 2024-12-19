from enum import Enum


class FlowComponentType(str, Enum):
    STEP = "STEP"  # individual API call, tool usage, or data processing step
    SUBFLOW = "SUBFLOW"  # a sequence of steps that may be reused
    ITERATOR = "ITERATOR"  # iterates over a collection of items
    FLOW = "FLOW"  # a standalone app that can integrate with the chat history manager
