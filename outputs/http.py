from typing import Any

import httpx

from context import CollectionContext
from exceptions import ConfigurationError, OutputError


class HttpOutput:
    destination = "HTTP"

    def __init__(self, url: str | None, token: str | None = None) -> None:
        self.url = url
        self.token = token

    def send(
        self,
        records: list[dict],
        context: CollectionContext,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        if not self.url:
            raise ConfigurationError(f"{self.destination} URL is not configured")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        payload = {"metadata": metadata or {}, "records": records}
        try:
            response = httpx.post(self.url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OutputError(f"{self.destination} unavailable: {exc}") from exc
        return len(records)
