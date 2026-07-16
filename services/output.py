from datetime import UTC, datetime
import json
import os
from typing import Any

import httpx

from exceptions import ConfigurationError, OutputError
from models import CollectionContext, Settings


def send(
    records: list[dict],
    context: CollectionContext,
    settings: Settings,
    *,
    asset: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    """Send parsed records to the requested output or the scope default."""
    destination = context.output or _default_destination(context.scope)
    output_metadata = {
        "scope": context.scope,
        "source": context.source,
        "data_type": context.data_type,
        "asset": asset or context.asset,
        "destination": destination,
        **(metadata or {}),
    }

    if destination == "file":
        return _send_file(records, context, settings, output_metadata)
    if destination == "stdout":
        print(json.dumps({"metadata": output_metadata, "records": records}, default=str))
        return len(records)
    return _send_http(records, destination, settings, output_metadata)


def _default_destination(scope: str) -> str:
    if scope == "pamela":
        return "backup_hub"
    if scope == "logstash":
        return "logstash"
    if scope == "baseline":
        return "referential"
    raise ConfigurationError(f"No output configured for scope: {scope}")


def _send_http(
    records: list[dict],
    destination: str,
    settings: Settings,
    metadata: dict[str, Any],
) -> int:
    if destination == "backup_hub":
        url, token, label = settings.backup_hub_url, settings.backup_hub_token, "Backup Hub"
    elif destination == "logstash":
        url, token, label = settings.logstash_url, settings.logstash_token, "Logstash"
    elif destination == "referential":
        url, token, label = (
            settings.referential_url,
            settings.referential_token,
            "Referential",
        )
    else:
        raise ConfigurationError(f"Unknown output: {destination}")

    if not url:
        raise ConfigurationError(f"{label} URL is not configured")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = httpx.post(
            url,
            json={"metadata": metadata, "records": records},
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OutputError(f"{label} unavailable: {exc}") from exc
    return len(records)


def _send_file(
    records: list[dict],
    context: CollectionContext,
    settings: Settings,
    metadata: dict[str, Any],
) -> int:
    now = datetime.now(UTC)
    directory = settings.output_dir / context.scope / context.source / context.data_type
    final_path = directory / f"{context.data_type}_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    temporary_path = final_path.with_suffix(".json.tmp")
    document_metadata = {
        "record_count": len(records),
        "collected_at": now.isoformat().replace("+00:00", "Z"),
        **metadata,
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
        raise OutputError(f"Cannot write file output: {exc}") from exc
    return len(records)
