from typing import Any

from context import CollectionContext
from exceptions import ConfigurationError
from modules.output.file import FileOutput
from modules.output.http import HttpOutput
from modules.output.stdout import StdoutOutput
from settings import Settings

DEFAULT_DESTINATIONS = {
    "pamela": "backup_hub",
    "logstash": "logstash",
    "baseline": "referential",
}


class OutputService:
    """Select and execute the final transport for a parsed collection."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(
        self,
        records: list[dict],
        context: CollectionContext,
        *,
        asset: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        destination = context.output or DEFAULT_DESTINATIONS.get(context.scope)
        if not destination:
            raise ConfigurationError(f"No output configured for scope: {context.scope}")

        output = self._build(destination)
        output_metadata = {
            "scope": context.scope,
            "source": context.source,
            "data_type": context.data_type,
            "asset": asset or context.asset,
            "destination": destination,
            **(metadata or {}),
        }
        return output.send(records, context, output_metadata)

    def _build(self, destination: str):
        if destination == "file":
            return FileOutput(self.settings.output_dir)
        if destination == "stdout":
            return StdoutOutput()

        http_destinations = {
            "backup_hub": (
                self.settings.backup_hub_url,
                self.settings.backup_hub_token,
                "Backup Hub",
            ),
            "logstash": (
                self.settings.logstash_url,
                self.settings.logstash_token,
                "Logstash",
            ),
            "referential": (
                self.settings.referential_url,
                self.settings.referential_token,
                "Referential",
            ),
        }
        try:
            url, token, label = http_destinations[destination]
        except KeyError as exc:
            raise ConfigurationError(f"Unknown output: {destination}") from exc
        return HttpOutput(url, token, label)
