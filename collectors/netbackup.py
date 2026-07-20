from typing import Any

from exceptions import CollectionError, ConfigurationError
from models import Asset, CollectionContext
from services import ssh


def create_api_client(asset: Asset) -> Any:
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


def create_ssh_client(asset: Asset, *, port: int = 22) -> Any:
    if not asset.ssh:
        raise ConfigurationError(f"NetBackup SSH is disabled for hostname={asset.hostname}")
    if not asset.ssh_username:
        raise ConfigurationError(f"NetBackup SSH username is missing for hostname={asset.hostname}")
    return ssh.create_client(
        asset.hostname,
        asset.ssh_username,
        asset.ssh_password,
        port=port,
    )


def collect_policies(client: Any) -> list[dict]:
    try:
        return _records(client.policies.list(include_details=False))
    except Exception as exc:
        raise CollectionError(f"NetBackup policies collection failed: {exc}") from exc


def collect_policy(client: Any, policy_name: str) -> dict:
    try:
        return _record(client.policies.get(policy_name))
    except Exception as exc:
        raise CollectionError(
            f"NetBackup policy details collection failed for policy={policy_name}: {exc}"
        ) from exc


def collect_jobs(client: Any, context: CollectionContext) -> list[dict]:
    try:
        return _records(client.jobs.list(**_date_parameters(context)))
    except Exception as exc:
        raise CollectionError(f"NetBackup jobs collection failed: {exc}") from exc


def collect_images(client: Any, context: CollectionContext) -> list[dict]:
    try:
        return _records(client.images.list(**_date_parameters(context)))
    except Exception as exc:
        raise CollectionError(f"NetBackup images collection failed: {exc}") from exc


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


def _records(items: list[Any]) -> list[dict]:
    return [_record(item) for item in items]


def _record(item: Any) -> dict:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    raise TypeError(f"Unsupported NetBackup record type: {type(item).__name__}")
