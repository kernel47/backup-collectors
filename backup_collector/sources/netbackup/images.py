from typing import Any

from backup_collector.context import CollectionContext
from backup_collector.sources.netbackup.jobs import _iso
from backup_collector.sources.netbackup.policies import _as_dict


def collect_images(client: Any, context: CollectionContext) -> list[dict]:
    hours = context.hours
    if hours is None and context.days is not None:
        hours = context.days * 24
    items = client.images.list(
        last_hours=hours,
        start_date=_iso(context.start_time),
        end_date=_iso(context.end_time),
    )
    return [_as_dict(item) for item in items]

