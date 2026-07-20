from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from exceptions import OutputError


def send(
    records: list[dict],
    output_dir: Path,
    *,
    scope: str,
    source: str,
    data_type: str,
    metadata: dict[str, Any],
) -> int:
    now = datetime.now(UTC)
    directory = output_dir / scope / source / data_type
    final_path = directory / f"{data_type}_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    temporary_path = final_path.with_suffix(".json.tmp")
    document = {
        "metadata": {
            "record_count": len(records),
            "collected_at": now.isoformat().replace("+00:00", "Z"),
            **metadata,
        },
        "records": records,
    }
    try:
        directory.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(
            json.dumps(document, indent=2, default=str),
            encoding="utf-8",
        )
        os.replace(temporary_path, final_path)
    except OSError as exc:
        raise OutputError(f"Cannot write file output: {exc}") from exc
    return len(records)
