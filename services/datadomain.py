from exceptions import CollectionError
from models import Asset, CollectionContext, CollectionResult


def collect(
    data_type: str,
    context: CollectionContext,
    asset: Asset,
) -> CollectionResult:
    del data_type, context, asset
    raise CollectionError("Data Domain collection is not implemented yet")
