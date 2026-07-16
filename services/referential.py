from typing import Any
from urllib.parse import quote

import httpx

from exceptions import CollectionError, ConfigurationError
from models import Asset, Settings


def get_asset(hostname: str, settings: Settings) -> Asset:
    """Resolve a hostname through the external referential API."""
    if not settings.referential_asset_url:
        raise ConfigurationError("REFERENTIAL_ASSET_URL is not configured")

    encoded_hostname = quote(hostname, safe="")
    if "{hostname}" in settings.referential_asset_url:
        url = settings.referential_asset_url.replace("{hostname}", encoded_hostname)
    else:
        url = f"{settings.referential_asset_url.rstrip('/')}/{encoded_hostname}"

    headers = {"Accept": "application/json"}
    if settings.referential_token:
        headers["Authorization"] = f"Bearer {settings.referential_token}"

    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CollectionError(f"Referential lookup failed for hostname={hostname}: {exc}") from exc

    data = _asset_data(payload, hostname)
    api_data = data.get("api_credentials") or data.get("api_config") or {}
    ssh_data = data.get("ssh_credentials") or data.get("ssh_config") or {}
    return Asset(
        hostname=str(data.get("hostname") or hostname),
        api_username=_first(
            data.get("api_username"), data.get("username"), api_data.get("username")
        ),
        api_password=_first(
            data.get("api_password"), data.get("password"), api_data.get("password")
        ),
        domain_type=str(data.get("domain_type") or api_data.get("domain_type") or ""),
        domain_name=str(data.get("domain_name") or api_data.get("domain_name") or ""),
        version=_first(data.get("version"), api_data.get("version")),
        ssh_username=_first(data.get("ssh_username"), ssh_data.get("username")),
        ssh_password=_first(data.get("ssh_password"), ssh_data.get("password")),
        api=_as_bool(data.get("api", False)),
        ssh=_as_bool(data.get("ssh", False)),
        region=data.get("region"),
        datacenter=data.get("datacenter"),
    )


def _asset_data(payload: Any, hostname: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            payload = data
    if isinstance(payload, list):
        match = next(
            (
                item
                for item in payload
                if isinstance(item, dict) and item.get("hostname") == hostname
            ),
            None,
        )
        if isinstance(match, dict):
            return match
    raise CollectionError(f"Referential returned no asset for hostname={hostname}")


def _first(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}
