from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
from typing import Any


@dataclass
class Asset:
    hostname: str
    api_username: str | None = None
    api_password: str | None = field(default=None, repr=False)
    domain_type: str = ""
    domain_name: str = ""
    version: str | None = None
    ssh_username: str | None = None
    ssh_password: str | None = field(default=None, repr=False)
    api: bool = False
    ssh: bool = False
    region: str | None = None
    datacenter: str | None = None


@dataclass
class CollectionContext:
    source: str
    data_type: str
    scope: str
    asset: str | None = None
    all_assets: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None
    hours: int | None = None
    days: int | None = None
    output: str | None = None
    dry_run: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionResult:
    source: str
    data_type: str
    asset: str
    records: list[dict[str, Any]]
    started_at: datetime
    finished_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def record_count(self) -> int:
        return len(self.records)


@dataclass
class ExecutionResult:
    source: str
    data_type: str
    scope: str
    collected_count: int
    parsed_count: int
    sent_count: int
    status: str
    duration_seconds: float
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Settings:
    backup_hub_url: str | None = None
    backup_hub_token: str | None = None
    logstash_url: str | None = None
    logstash_token: str | None = None
    referential_url: str | None = None
    referential_token: str | None = None
    referential_asset_url: str | None = None
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
            referential_asset_url=os.getenv("REFERENTIAL_ASSET_URL"),
            output_dir=Path(os.getenv("BACKUP_COLLECTOR_OUTPUT_DIR", cls.output_dir)),
            log_level=os.getenv("BACKUP_COLLECTOR_LOG_LEVEL", "WARNING"),
        )
