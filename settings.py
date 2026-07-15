from dataclasses import dataclass
import os
from pathlib import Path


@dataclass
class Settings:
    backup_hub_url: str | None = None
    backup_hub_token: str | None = None
    logstash_url: str | None = None
    logstash_token: str | None = None
    referential_url: str | None = None
    referential_token: str | None = None
    output_dir: Path = Path("/var/lib/backup-collector/outbox")
    log_level: str = "WARNING"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            backup_hub_url=os.getenv("BACKUP_HUB_URL"),
            backup_hub_token=os.getenv("BACKUP_HUB_TOKEN"),
            logstash_url=os.getenv("LOGSTASH_URL"),
            logstash_token=os.getenv("LOGSTASH_TOKEN"),
            referential_url=os.getenv("REFERENTIAL_URL"),
            referential_token=os.getenv("REFERENTIAL_TOKEN"),
            output_dir=Path(os.getenv("BACKUP_COLLECTOR_OUTPUT_DIR", cls.output_dir)),
            log_level=os.getenv("BACKUP_COLLECTOR_LOG_LEVEL", "WARNING"),
        )
