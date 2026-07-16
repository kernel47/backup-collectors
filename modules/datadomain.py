from context import CollectionContext
from exceptions import CollectionError
from result import CollectionResult


def collect(data_type: str, context: CollectionContext) -> CollectionResult:
    del data_type, context
    raise CollectionError("Data Domain collection is not implemented yet")

