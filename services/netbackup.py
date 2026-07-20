from typing import Any

from exceptions import CollectionError, ConfigurationError
from models import Asset, CollectionContext, CollectionResult


def collect(
    data_type: str,
    context: CollectionContext,
    asset: Asset,
    client: Any = None,
) -> CollectionResult:
    owns_client = client is None
    if client is None:
        client = create_client(asset)

    try:
        try:
            if data_type == "policies":
                items = client.policies.list(include_details=True)
            elif data_type == "clients":
                items = client.policies.clients()
            elif data_type == "jobs":
                items = client.jobs.list(**_date_parameters(context))
            elif data_type == "images":
                items = client.images.list(**_date_parameters(context))
            else:
                raise CollectionError(f"Unsupported NetBackup data type: {data_type}")
            records = [_as_dict(item) for item in items]
        except CollectionError:
            raise
        except Exception as exc:
            raise CollectionError(f"NetBackup {data_type} collection failed: {exc}") from exc

        return CollectionResult(asset=asset.hostname, records=records)
    finally:
        if owns_client and hasattr(client, "close"):
            client.close()


def create_client(asset: Asset) -> Any:
    if not asset.api:
        raise ConfigurationError(f"NetBackup API is disabled for hostname={asset.hostname}")
    try:
        from nbu import NetBackup
    except ImportError as exc:
        raise ConfigurationError("The netbackup-py package is not installed") from exc
    return NetBackup(
        master=asset.hostname,
        username=asset.api_username,
        password=asset.api_password,
        domain_type=asset.domain_type,
        domain_name=asset.domain_name,
        version=asset.version,
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
