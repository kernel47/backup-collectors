from typing import Any

from backup_collector.context import CollectionContext


def send_baseline_result(
    records: list[dict], context: CollectionContext, output: Any, asset: str | None = None
) -> int:
    return output.send(
        records,
        context,
        {"scope": "baseline", "workflow": "baseline", "asset": asset},
    )
