from abc import abstractmethod, ABC
from typing import List, Generic, TypeVar

T = TypeVar('T')


# Define the generic Source abstract class
class Source(ABC, Generic[T]):
    @abstractmethod
    def extract(self, key: str) -> T:
        """Extract data from the source and return it as type T."""
        pass

    @abstractmethod
    def list(self, prefix: str = '') -> List[str]:
        """List all keys in the source, optionally filtered by a prefix (e.g., folder)."""
        pass
