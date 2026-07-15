from typing import Any

from context import CollectionContext
from result import CollectionResult


class TapeLibrarySource:
    def __init__(self, client: Any = None) -> None:
        self.client = client

    def collect(self, data_type: str, context: CollectionContext) -> CollectionResult:
        raise NotImplementedError("Tape Library source is not implemented yet")
