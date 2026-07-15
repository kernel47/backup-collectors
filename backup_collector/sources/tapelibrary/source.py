from typing import Any

from backup_collector.context import CollectionContext
from backup_collector.result import CollectionResult


class TapeLibrarySource:
    def __init__(self, client: Any = None) -> None:
        self.client = client

    def collect(self, data_type: str, context: CollectionContext) -> CollectionResult:
        raise NotImplementedError("Tape Library source is not implemented yet")
