from abc import ABC, abstractmethod
from typing import Any


class AbstractRerankClient(ABC):
    """
    A simple wrapper for reranker client interface
    """

    @abstractmethod
    def rerank(self, *args, **kwargs) -> Any:
        """
        A simple wrapper for reranker client. Since different reranker clients may have
        very different interfaces, we use this method to wrap the reranker client to
        avoid unnecessary dependencies.
        """
        pass
