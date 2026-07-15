import json
from typing import Any

from context import CollectionContext


class StdoutOutput:
    def send(
        self,
        records: list[dict],
        context: CollectionContext,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        print(json.dumps({"metadata": metadata or {}, "records": records}, default=str))
        return len(records)

