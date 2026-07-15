from datetime import UTC, datetime
from typing import Any, Callable

from backup_collector.context import CollectionContext
from backup_collector.exceptions import CollectionError
from backup_collector.result import CollectionResult
from backup_collector.sources.netbackup.images import collect_images
from backup_collector.sources.netbackup.jobs import collect_jobs
from backup_collector.sources.netbackup.policies import collect_policies
from backup_collector.sources.netbackup.shares import collect_shares

Collector = Callable[[Any, CollectionContext], list[dict]]

COLLECTORS: dict[str, Collector] = {
    "policies": collect_policies,
    "jobs": collect_jobs,
    "images": collect_images,
    "shares": collect_shares,
}


class NetBackupSource:
    def __init__(self, client: Any) -> None:
        self.client = client

    def collect(self, data_type: str, context: CollectionContext) -> CollectionResult:
        collector = COLLECTORS.get(data_type)
        if collector is None:
            raise CollectionError(f"Unsupported NetBackup data type: {data_type}")
        started_at = datetime.now(UTC)
        try:
            records = collector(self.client, context)
        except Exception as exc:
            raise CollectionError(f"NetBackup {data_type} collection failed: {exc}") from exc
        return CollectionResult(
            source="netbackup",
            data_type=data_type,
            asset=context.asset or getattr(getattr(self.client, "config", None), "master", "unknown"),
            records=records,
            started_at=started_at,
            finished_at=datetime.now(UTC),
        )

