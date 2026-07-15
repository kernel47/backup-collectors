from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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

