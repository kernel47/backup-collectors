from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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

