from typing import Any

from context import CollectionContext
from modules.netbackup.policies import _as_dict


def _iso(value: object) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def collect_jobs(client: Any, context: CollectionContext) -> list[dict]:
    hours = context.hours
    if hours is None and context.days is not None:
        hours = context.days * 24
    items = client.jobs.list(
        last_hours=hours,
        start_date=_iso(context.start_time),
        end_date=_iso(context.end_time),
    )
    return [_as_dict(item) for item in items]

