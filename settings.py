from dataclasses import dataclass
import os
from pathlib import Path

from exceptions import ConfigurationError


def _optional_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}


@dataclass
class Settings:
    nbu_host: str | None = None
    nbu_username: str | None = None
    nbu_password: str | None = None
    nbu_verify_tls: bool = True
    backup_hub_url: str | None = None
    backup_hub_token: str | None = None
    logstash_url: str | None = None
    logstash_token: str | None = None
    reference_url: str | None = None
    reference_token: str | None = None
    output_dir: Path = Path("/var/lib/backup-collector/outbox")
    log_level: str = "WARNING"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            nbu_host=os.getenv("NBU_HOST") or os.getenv("NBU_MASTER"),
            nbu_username=os.getenv("NBU_USERNAME"),
            nbu_password=os.getenv("NBU_PASSWORD"),
            nbu_verify_tls=_optional_bool("NBU_VERIFY_TLS", _optional_bool("NBU_VERIFY_SSL")),
            backup_hub_url=os.getenv("BACKUP_HUB_URL"),
            backup_hub_token=os.getenv("BACKUP_HUB_TOKEN"),
            logstash_url=os.getenv("LOGSTASH_URL"),
            logstash_token=os.getenv("LOGSTASH_TOKEN"),
            reference_url=os.getenv("REFERENCE_URL"),
            reference_token=os.getenv("REFERENCE_TOKEN"),
            output_dir=Path(os.getenv("BACKUP_COLLECTOR_OUTPUT_DIR", cls.output_dir)),
            log_level=os.getenv("BACKUP_COLLECTOR_LOG_LEVEL", "WARNING"),
        )

    def require_netbackup(self, asset: str | None = None) -> None:
        missing = []
        if not (asset or self.nbu_host):
            missing.append("NBU_HOST")
        if not self.nbu_username:
            missing.append("NBU_USERNAME")
        if not self.nbu_password:
            missing.append("NBU_PASSWORD")
        if missing:
            raise ConfigurationError(f"Missing NetBackup configuration: {', '.join(missing)}")

