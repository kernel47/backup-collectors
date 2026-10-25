"""Existing Reference client; URL and payload contract must be confirmed by the owner."""

from urllib.parse import quote

import httpx

from core.exceptions import CollectionError, ConfigurationError
from core.models import Asset, Settings


def get_asset(asset: str, settings: Settings) -> Asset:
    # Preserve the existing configured URL behavior; do not invent an API route.
    url = settings.backup_reference_url
    if not url:
        raise ConfigurationError("BACKUP_REFERENCE_URL or REFERENTIAL_ASSET_URL is required")
    encoded = quote(asset, safe="")
    if "{asset_id}" in url or "{hostname}" in url:
        url = url.replace("{asset_id}", encoded).replace("{hostname}", encoded)
    else:
        url = f"{url.rstrip('/')}/{encoded}"
    headers = {"Accept": "application/json"}
    if settings.backup_reference_token:
        headers["Authorization"] = f"Bearer {settings.backup_reference_token}"
    try:
        response = httpx.get(url, headers=headers, timeout=settings.backup_reference_timeout)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise CollectionError("Backup Reference lookup failed") from None
    data = _asset_data(payload, asset)
    for key in ("master_server", "region", "technology", "hostname"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise CollectionError(f"Backup Reference asset missing {key}")
    if data["technology"].lower() != "netbackup":
        raise CollectionError("Only NetBackup assets are currently supported")
    if data.get("asset_id", asset) != asset:
        raise CollectionError("Backup Reference returned a different asset_id")
    api = data.get("api_credentials") or data.get("api_config") or {}
    ssh = data.get("ssh_credentials") or data.get("ssh_config") or {}
    return Asset(
        asset=asset,
        master_server=data["master_server"],
        hostname=data["hostname"],
        region=data["region"],
        technology="netbackup",
        api_endpoint=data.get("api_endpoint"),
        connection_method=data.get("connection_method", "rest"),
        api_username=data.get("api_username", api.get("username")),
        api_password=data.get("api_password", api.get("password")),
        api_token=data.get("api_token", api.get("token")),
        domain_type=data.get("domain_type", api.get("domain_type", "")),
        domain_name=data.get("domain_name", api.get("domain_name", "")),
        version=data.get("version", api.get("version")),
        ssh_username=data.get("ssh_username", ssh.get("username")),
        ssh_password=data.get("ssh_password", ssh.get("password")),
        ssh_port=data.get("ssh_port", ssh.get("port", 22)),
        ssh_options=data.get("ssh_options", ssh.get("options", {})),
        api=_as_bool(data.get("api", True)),
        ssh=_as_bool(data.get("ssh", False)),
    )


def _asset_data(payload, asset):
    if isinstance(payload, dict):
        payload = payload.get("data", payload)
    if isinstance(payload, list):
        payload = next(
            (
                v
                for v in payload
                if isinstance(v, dict) and v.get("asset_id", v.get("hostname")) == asset
            ),
            None,
        )
    if not isinstance(payload, dict) or not payload:
        raise CollectionError("Backup Reference returned no asset")
    return payload


def _as_bool(value):
    return value is True or str(value).lower() in {"1", "true", "yes", "on"}
