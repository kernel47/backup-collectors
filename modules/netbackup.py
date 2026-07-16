from datetime import UTC, datetime
from typing import Any

from context import CollectionContext
from exceptions import CollectionError, ConfigurationError
from result import CollectionResult


def create_client(master_server: str) -> Any:
    """Create netbackup-py with only the master server hostname."""
    if not master_server:
        raise ConfigurationError("Use --asset MASTER_SERVER for a NetBackup collection")
    try:
        from nbu import NetBackup
    except ImportError as exc:
        raise ConfigurationError("The netbackup-py package is not installed") from exc
    return NetBackup(master=master_server)


def collect(client: Any, data_type: str, context: CollectionContext) -> CollectionResult:
    """Collect one NetBackup data type with explicit, easy-to-follow branches."""
    started_at = datetime.now(UTC)
    try:
        if data_type == "policies":
            items = client.policies.list(include_details=True)
        elif data_type == "jobs":
            items = client.jobs.list(**_date_parameters(context))
        elif data_type == "images":
            items = client.images.list(**_date_parameters(context))
        elif data_type == "shares":
            # Temporary adapter until netbackup-py exposes a dedicated shares service.
            items = client.policies.clients()
        else:
            raise CollectionError(f"Unsupported NetBackup data type: {data_type}")
        records = [_as_dict(item) for item in items]
    except CollectionError:
        raise
    except Exception as exc:
        raise CollectionError(f"NetBackup {data_type} collection failed: {exc}") from exc

    asset = context.asset or getattr(getattr(client, "config", None), "master", "unknown")
    return CollectionResult(
        source="netbackup",
        data_type=data_type,
        asset=asset,
        records=records,
        started_at=started_at,
        finished_at=datetime.now(UTC),
    )


def _date_parameters(context: CollectionContext) -> dict[str, Any]:
    hours = context.hours
    if hours is None and context.days is not None:
        hours = context.days * 24
    return {
        "last_hours": hours,
        "start_date": _iso(context.start_time),
        "end_date": _iso(context.end_time),
    }


def _iso(value: object) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _as_dict(item: Any) -> dict:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    raise TypeError(f"Unsupported NetBackup record type: {type(item).__name__}")

