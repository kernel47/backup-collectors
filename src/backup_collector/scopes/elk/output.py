from typing import Any

from backup_collector.context import CollectionContext


def send_elk_result(
    records: list[dict], context: CollectionContext, output: Any, asset: str | None = None
) -> int:
    return output.send(
        records,
        context,
        {"scope": "elk", "data_type": context.data_type, "asset": asset},
    )
