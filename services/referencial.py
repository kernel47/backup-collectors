"""Existing Referencial client; URL and payload contract must be confirmed by the owner."""

from dataclasses import fields
from urllib.parse import quote

import httpx

from core.exceptions import CollectionError, ConfigurationError
from core.models import Asset, Settings


def get_asset(asset: str, settings: Settings) -> Asset:
    # Preserve the existing configured URL behavior; do not invent an API route.
    url = settings.backup_referencial_asse_url
    if not url:
        raise ConfigurationError("BACKUP_REFERENCIAL_ASSE_URL is required")
    encoded = quote(asset, safe="")
    if "{hostname}" in url:
        url = url.replace("{hostname}", encoded)
    else:
        url = f"{url.rstrip('/')}/{encoded}"
    headers = {"Accept": "application/json"}
    if settings.backup_referencial_token:
        headers["Authorization"] = f"Bearer {settings.backup_referencial_token}"
    try:
        response = httpx.get(url, headers=headers, timeout=settings.backup_referencial_timeout)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise CollectionError("Backup Referencial lookup failed") from error
    data = _asset_data(payload, asset)
    for key in ("hostname", "region", "technology"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise CollectionError(f"Backup Referencial asset missing {key}")
    if data["hostname"] != asset:
        raise CollectionError("Backup Referencial returned a different hostname")
    if data["technology"].lower() != "netbackup":
        raise CollectionError("Only NetBackup assets are currently supported")
    values = {f.name: data[f.name] for f in fields(Asset) if f.name in data}
    for key in ("active", "api", "ssh", "is_naas"):
        if key in values:
            values[key] = _as_bool(values[key])
    result = Asset(**values)
    if not result.active:
        raise ConfigurationError("Asset is inactive")
    return result


def _asset_data(payload, asset):
    if isinstance(payload, dict):
        payload = payload.get("data", payload)
    if isinstance(payload, list):
        payload = next(
            (
                v
                for v in payload
                if isinstance(v, dict) and v.get("hostname") == asset
            ),
            None,
        )
    if not isinstance(payload, dict) or not payload:
        raise CollectionError("Backup Referencial returned no asset")
    return payload


def _as_bool(value):
    return value is True or str(value).lower() in {"1", "true", "yes", "on"}
