from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from context import CollectionContext
from exceptions import OutputError


class JsonFileOutput:
    def __init__(self, output_dir: Path | str) -> None:
        self.output_dir = Path(output_dir)

    def send(
        self,
        records: list[dict],
        context: CollectionContext,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        now = datetime.now(UTC)
        directory = self.output_dir / context.scope / context.source / context.data_type
        filename = f"{context.data_type}_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
        final_path = directory / filename
        temporary_path = final_path.with_suffix(".json.tmp")
        document_metadata = {
            "scope": context.scope,
            "source": context.source,
            "data_type": context.data_type,
            "asset": context.asset,
            "record_count": len(records),
            "collected_at": now.isoformat().replace("+00:00", "Z"),
            **(metadata or {}),
        }
        try:
            directory.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(
                    {"metadata": document_metadata, "records": records},
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            os.replace(temporary_path, final_path)
        except OSError as exc:
            raise OutputError(f"Cannot write JSON output: {exc}") from exc
        return len(records)
