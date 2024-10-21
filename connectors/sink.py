from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar('T')


# Define the generic Sink abstract class
class Sink(ABC, Generic[T]):
    @abstractmethod
    def load(self, data: T, key: str):
        """Load data into the sink (e.g., upload to S3) with the given key."""
        pass
