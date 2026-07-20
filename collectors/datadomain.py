from exceptions import CollectionError
from models import Asset, CollectionContext


def collect(data_type: str, context: CollectionContext, asset: Asset) -> list[dict]:
    del data_type, context, asset
    raise CollectionError("Data Domain collection is not implemented yet")
