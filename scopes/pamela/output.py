from typing import Any

from context import CollectionContext


def send_pamela_result(
    records: list[dict], context: CollectionContext, output: Any, asset: str | None = None
) -> int:
    return output.send(
        records,
        context,
        {"scope": "pamela", "data_type": context.data_type, "asset": asset},
    )
