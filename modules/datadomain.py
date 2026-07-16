from exceptions import CollectionError
from models import CollectionContext, CollectionResult


def collect(data_type: str, context: CollectionContext) -> CollectionResult:
    del data_type, context
    raise CollectionError("Data Domain collection is not implemented yet")
