from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from typing import Any, Iterable


def policies(
    records: list[dict],
    *,
    types: Iterable[str] = (),
    names: Iterable[str] = (),
) -> list[dict]:
    allowed_types = {value.casefold() for value in types}
    name_patterns = [value.casefold() for value in names]

    def keep(record: dict) -> bool:
        policy_type = str(record.get("policy_type") or "").casefold()
        policy_name = str(record.get("policy_name") or record.get("name") or "").casefold()
        type_matches = not allowed_types or policy_type in allowed_types
        name_matches = not name_patterns or any(
            fnmatch(policy_name, pattern) for pattern in name_patterns
        )
        return type_matches and name_matches

    return [record for record in records if keep(record)]


def dates(
    records: list[dict],
    *,
    fields: tuple[str, ...],
    start: datetime | None = None,
    end: datetime | None = None,
    hours: int | None = None,
    days: int | None = None,
) -> list[dict]:
    if start is None and hours is not None:
        start = datetime.now(UTC) - timedelta(hours=hours)
    if start is None and days is not None:
        start = datetime.now(UTC) - timedelta(days=days)
    if start is None and end is None:
        return records

    start = _utc(start) if start else None
    end = _utc(end) if end else None
    filtered = []
    for record in records:
        value = next((record.get(field) for field in fields if record.get(field) is not None), None)
        record_date = _datetime(value)
        if record_date is None:
            continue
        if start and record_date < start:
            continue
        if end and record_date > end:
            continue
        filtered.append(record)
    return filtered


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _utc(value)
    if not value:
        return None
    try:
        return _utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
