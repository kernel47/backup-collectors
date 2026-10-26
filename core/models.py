import math
import os
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from uuid import uuid4


@dataclass
class Asset:
    hostname: str
    admin_name: str = ""
    active: bool = True
    region: str = ""
    technology: str = "netbackup"
    datacenter: str = ""
    api_username: str | None = None
    api_password: str | None = field(default=None, repr=False)
    domain_name: str = ""
    domain_type: str = ""
    version: str | None = None
    ssh_username: str | None = None
    ssh_password: str | None = field(default=None, repr=False)
    ssh: bool = False
    api: bool = True
    is_naas: bool = False


@dataclass
class CollectionContext:
    type: str
    asset: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    hours: float | None = None
    scope: str = "netbackup"
    dry_run: bool = False
    debug: bool = False

    def __post_init__(self):
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("--asset is required")
        if self.type not in {"jobs", "images", "policies", "slps", "images-contents"}:
            raise ValueError("Unknown collection type")
        if self.type not in {"jobs", "images", "images-contents"}:
            if self.hours is not None or self.start_date is not None or self.end_date is not None:
                raise ValueError("Dates and --hours apply only to jobs, images and images-contents")
            return
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("--start-date and --end-date must be supplied together")
        if self.start_date is not None:
            if self.hours is not None:
                raise ValueError("Use --hours or --start-date/--end-date")
            if any(
                not isinstance(d, datetime) or d.tzinfo is None
                for d in (self.start_date, self.end_date)
            ):
                raise ValueError("Dates require a timezone")
            if self.start_date >= self.end_date:
                raise ValueError("--start-date must precede --end-date")
        else:
            self.hours = 24 if self.hours is None else self.hours
            if isinstance(self.hours, bool) or not math.isfinite(self.hours) or self.hours <= 0:
                raise ValueError("--hours must be positive and finite")


@dataclass
class Settings:
    backup_referencial_url: str = ""
    backup_referencial_asse_url: str = ""
    backup_referencial_token: str = field(default="", repr=False)
    backup_referencial_timeout: float = 15.0
    opensearch_url: str = ""
    opensearch_username: str = ""
    opensearch_password: str = field(default="", repr=False)
    opensearch_verify_ssl: bool = True
    opensearch_ca_cert: str = ""
    opensearch_timeout: float = 30.0
    opensearch_batch_size: int = 500
    opensearch_configuration_batch_size: int = 50
    opensearch_max_batch_mb: float = 10.0
    opensearch_max_retries: int = 3
    opensearch_script_jobs: str = "backup_jobs_upsert"
    opensearch_script_images: str = "backup_images_upsert"
    opensearch_script_configurations: str = "backup_configuration_upsert"
    history_max_versions: int = 10
    netbackup_verify_ssl: bool = True
    netbackup_ca_cert: str = ""
    netbackup_timeout: float = 60.0
    log_level: str = "INFO"

    def __post_init__(self):
        for name in (
            "backup_referencial_timeout",
            "opensearch_timeout",
            "netbackup_timeout",
            "opensearch_max_batch_mb",
            "opensearch_batch_size",
            "opensearch_configuration_batch_size",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name.upper()} must be positive and finite")
        if self.opensearch_max_retries < 0 or not 0 <= self.history_max_versions <= 2147483647:
            raise ValueError("Invalid retry/history limits")
        for name in (
            "opensearch_script_jobs",
            "opensearch_script_images",
            "opensearch_script_configurations",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name.upper()} must not be empty")

    @classmethod
    def from_env(cls):
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=".env", override=False)
        values = {}
        for f in fields(cls):
            value = os.getenv(f.name.upper())
            if value is None:
                continue
            if isinstance(f.default, bool):
                if value.lower() not in {"true", "false", "1", "0"}:
                    raise ValueError(f"Invalid boolean: {f.name.upper()}")
                value = value.lower() in {"true", "1"}
            elif isinstance(f.default, int):
                value = int(value)
            elif isinstance(f.default, float):
                value = float(value)
            values[f.name] = value
        return cls(**values)


@dataclass(frozen=True)
class ParsedDocument:
    """Validated document produced by a connector parser, ready for its sink."""

    identifier: str
    data: dict


@dataclass
class CollectionStats:
    status: str = "failed"
    collected: int = 0
    invalid: int = 0
    excluded: int = 0


@dataclass
class StorageStats:
    status: str = "failed"
    destination: str = "opensearch"
    index: str | None = None
    created: int = 0
    updated: int = 0
    noop: int = 0
    failed: int = 0
    displayed: int = 0

    @property
    def confirmed(self):
        return (
            self.displayed
            if self.destination == "console"
            else self.created + self.updated + self.noop
        )


@dataclass
class PerformanceStats:
    cpu_user_seconds: float
    cpu_system_seconds: float
    cpu_total_seconds: float
    cpu_average_percent: float
    python_peak_bytes: int | None
    process_peak_rss_bytes: int


@dataclass
class CollectionReport:
    schema_version: str = "1.0"
    collection_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "failed"
    asset_id: str | None = None
    master_server: str | None = None
    region: str | None = None
    technology: str | None = None
    resource: str | None = None
    collection: CollectionStats = field(default_factory=CollectionStats)
    storage: StorageStats = field(default_factory=StorageStats)
    duration_seconds: float = 0
    performance: PerformanceStats | None = None
    errors: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_context(cls, context):
        return cls(
            asset_id=context.asset,
            technology=context.scope,
            resource=context.type,
            storage=StorageStats(
                destination="console" if context.dry_run else "opensearch",
                index=None if context.dry_run else f"backup-{context.type}",
            ),
        )

    def add_error(self, stage, code, message=None):
        if len(self.errors) < 20:
            error = {"stage": stage, "code": code}
            if message:
                error["message"] = message
            self.errors.append(error)

    def finish(self, completed, duration):
        valid = self.collection.collected - self.collection.invalid
        self.collection.status = (
            "success"
            if completed and not self.collection.invalid
            else "partial"
            if valid
            else "failed"
        )
        storage_error = self.storage.failed or any(e["stage"] == "storage" for e in self.errors)
        self.storage.status = (
            ("partial" if self.storage.confirmed else "failed")
            if storage_error
            else "success"
            if completed or self.storage.confirmed
            else "failed"
        )
        if self.collection.status == self.storage.status == "success" and not self.errors:
            self.status = "success"
        else:
            self.status = "partial" if self.storage.confirmed else "failed"
        self.duration_seconds = round(duration, 3)

    @property
    def exit_code(self):
        return {"success": 0, "failed": 1, "partial": 2}[self.status]

    def to_dict(self):
        result = asdict(self)
        if self.performance is None:
            result.pop("performance")
        if self.storage.destination != "console":
            result["storage"].pop("displayed")
        return result
