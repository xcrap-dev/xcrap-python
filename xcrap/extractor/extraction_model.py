from abc import ABC, abstractmethod


class ExtractionModel(ABC):
    """
    Abstract base class for all extraction models.
    """

    @abstractmethod
    def extract(self, content: str) -> any:
        pass
