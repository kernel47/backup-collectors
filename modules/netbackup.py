"""Minimal wrapper around the external netbackup-py package."""

from typing import Any

from exceptions import ConfigurationError
from models import Asset


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
