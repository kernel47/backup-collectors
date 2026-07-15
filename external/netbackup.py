from typing import Any

from exceptions import ConfigurationError


def create_client(master_server: str) -> Any:
    """Create an nbu client using only the master server hostname.

    Authentication and configuration lookup belong to netbackup-py. Backup Collector
    deliberately does not receive or store NetBackup credentials.
    """
    if not master_server:
        raise ConfigurationError(
            "A NetBackup master server hostname is required; use --asset MASTER_SERVER"
        )
    try:
        from nbu import NetBackup
    except ImportError as exc:
        raise ConfigurationError("The netbackup-py package is not installed") from exc
    return NetBackup(master=master_server)

