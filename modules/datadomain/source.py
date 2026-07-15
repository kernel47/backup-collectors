from typing import Any

from context import CollectionContext
from result import CollectionResult


class DataDomainSource:
    def __init__(self, client: Any = None) -> None:
        self.client = client

    def collect(self, data_type: str, context: CollectionContext) -> CollectionResult:
        raise NotImplementedError("Data Domain source is not implemented yet")

