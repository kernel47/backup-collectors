import json
from typing import Any

from exceptions import ConfigurationError
from models import CollectionContext, Settings
from services import file_output, http_output, logstash_output


def send(
    records: list[dict],
    context: CollectionContext,
    settings: Settings,
    *,
    data_type: str,
    asset: str,
    metadata: dict[str, Any] | None = None,
) -> int:
    destination = destination_for(context)
    output_metadata = {
        "scope": context.scope,
        "source": context.source,
        "data_type": data_type,
        "asset": asset,
        "destination": destination,
        **(metadata or {}),
    }

    if destination == "file":
        return file_output.send(
            records,
            settings.output_dir,
            scope=context.scope,
            source=context.source,
            data_type=data_type,
            metadata=output_metadata,
        )
    if destination == "stdout":
        print(json.dumps({"metadata": output_metadata, "records": records}, default=str))
        return len(records)
    if destination == "logstash":
        if not settings.logstash_url:
            raise ConfigurationError("Logstash URL is not configured")
        return logstash_output.send(
            records,
            settings.logstash_url,
            metadata=output_metadata,
            token=settings.logstash_token,
        )

    url, token = _http_destination(destination, settings)
    return http_output.send(records, url, metadata=output_metadata, token=token)


def destination_for(context: CollectionContext) -> str:
    if context.output:
        return context.output
    if context.scope == "pamela":
        return "backup_hub"
    if context.scope == "logstash":
        return "logstash"
    if context.scope == "baseline":
        return "referential"
    raise ConfigurationError(f"No output configured for scope: {context.scope}")


def _http_destination(destination: str, settings: Settings) -> tuple[str, str | None]:
    if destination == "backup_hub" and settings.backup_hub_url:
        return settings.backup_hub_url, settings.backup_hub_token
    if destination == "referential" and settings.referential_url:
        return settings.referential_url, settings.referential_token
    if destination in {"backup_hub", "referential"}:
        raise ConfigurationError(f"{destination} URL is not configured")
    raise ConfigurationError(f"Unknown output: {destination}")
