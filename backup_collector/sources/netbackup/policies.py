from typing import Any

from backup_collector.context import CollectionContext


def _as_dict(item: Any) -> dict:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    raise TypeError(f"Unsupported NetBackup record type: {type(item).__name__}")


def collect_policies(client: Any, context: CollectionContext) -> list[dict]:
    del context
    return [_as_dict(item) for item in client.policies.list(include_details=True)]

