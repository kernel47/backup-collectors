from typing import Any

import httpx

from exceptions import OutputError


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    token: str | None = None,
    timeout: float = 30.0,
) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OutputError(f"HTTP output unavailable: {exc}") from exc


def send(
    records: list[dict],
    url: str,
    *,
    metadata: dict[str, Any],
    token: str | None = None,
    timeout: float = 30.0,
) -> int:
    post_json(
        url,
        {"metadata": metadata, "records": records},
        token=token,
        timeout=timeout,
    )
    return len(records)
