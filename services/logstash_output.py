from typing import Any

from services import http_output


def send(
    records: list[dict],
    url: str,
    *,
    metadata: dict[str, Any],
    token: str | None = None,
    timeout: float = 30.0,
) -> int:
    """Send one parsed collection to the Logstash HTTP input."""
    return http_output.send(
        records,
        url,
        metadata=metadata,
        token=token,
        timeout=timeout,
    )
