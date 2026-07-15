from typing import Any

from backup_collector.context import CollectionContext


class BaselineCollector:
    """Coordinates the NetBackup datasets needed by the baseline workflow."""

    def collect(self, source: Any, context: CollectionContext) -> dict[str, list[dict]]:
        policies = source.collect("policies", context)
        return {"policies": policies.records}

