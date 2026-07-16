"""Minimal wrapper around the external netbackup-py package."""

from typing import Any

from exceptions import ConfigurationError


def create_client(master_server: str) -> Any:
    if not master_server:
        raise ConfigurationError("Use --asset MASTER_SERVER for a NetBackup collection")
    try:
        from nbu import NetBackup
    except ImportError as exc:
        raise ConfigurationError("The netbackup-py package is not installed") from exc
    return NetBackup(master=master_server)

