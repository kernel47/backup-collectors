"""Shared NetBackup client construction."""

import os

from core.exceptions import ConfigurationError
from core.models import Asset, Settings
from services.ssh import SSHClient


def create_api_client(asset: Asset, settings: Settings):
    if not asset.api or asset.connection_method != "rest":
        raise ConfigurationError("NetBackup REST is not enabled for this asset")
    from nbu import NetBackup

    # The pinned config supports bool verify_ssl only. httpx reads SSL_CERT_FILE
    # while constructing its TLS context; restore the environment immediately.
    previous_ca = os.environ.get("SSL_CERT_FILE")
    if settings.netbackup_ca_cert:
        os.environ["SSL_CERT_FILE"] = settings.netbackup_ca_cert
    try:
        return NetBackup(
            master=asset.hostname,
            base_url=asset.api_endpoint,
            username=asset.api_username,
            password=asset.api_password,
            token=asset.api_token,
            domain_type=asset.domain_type,
            domain_name=asset.domain_name,
            version=asset.version,
            verify_ssl=settings.netbackup_verify_ssl,
            timeout=settings.netbackup_timeout,
        )
    finally:
        if settings.netbackup_ca_cert:
            if previous_ca is None:
                os.environ.pop("SSL_CERT_FILE", None)
            else:
                os.environ["SSL_CERT_FILE"] = previous_ca


def create_ssh_client(asset: Asset):
    if not asset.ssh:
        return None
    if not asset.ssh_username:
        raise ConfigurationError("NetBackup SSH username is missing")
    if (
        isinstance(asset.ssh_port, bool)
        or not isinstance(asset.ssh_port, int)
        or not 1 <= asset.ssh_port <= 65535
    ):
        raise ConfigurationError("NetBackup SSH port must be an integer between 1 and 65535")
    if not isinstance(asset.ssh_options, dict):
        raise ConfigurationError("NetBackup SSH options must be an object")
    return SSHClient(
        host=asset.hostname,
        username=asset.ssh_username,
        password=asset.ssh_password,
        port=asset.ssh_port,
        options=asset.ssh_options.copy(),
    )


def date_parameters(*, hours=None, start_date=None, end_date=None):
    """Translate our hours parameter to netbackup-py's external last_hours keyword."""
    return {
        "last_hours": (hours if hours is not None else 24) if start_date is None else None,
        "start_date": start_date.isoformat() if start_date is not None else None,
        "end_date": end_date.isoformat() if end_date is not None else None,
    }
