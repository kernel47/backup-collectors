"""Technical document preparation: identity, dates, sanitization and fingerprint."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from core.exceptions import ParsingError
from core.models import ParsedDocument

IDENTITIES = {
    "jobs": ("job_id", "start_time"),
    "images": ("image_id",),
    "policies": ("name",),
    "slps": ("name",),
    "images-contents": ("image_id", "path"),
}
NAMESPACE = uuid5(NAMESPACE_URL, "urn:backup-index:documents:v1")
METADATA = {
    "master_server",
    "region",
    "technology",
    "created_at",
    "collected_at",
    "updated_at",
    "hash",
    "history",
    "source",
}
SECRET_KEYS = {"password", "token", "authorization", "credentials", "secret", "apikey"}


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def timestamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ParsingError("A timezone-aware ISO-8601 date is required")
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def identity_text(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise ParsingError("Missing or invalid identity component")
    return str(value)


def document_id(kind, document):
    values = [kind, document.get("master_server")]
    for key in IDENTITIES[kind]:
        value = document.get(key)
        if key == "start_time":
            value = timestamp(value)
        if key == "job_id":
            text = identity_text(value)
            value = str(int(text)) if text.isdecimal() else text
        values.append(value)
    return str(
        uuid5(
            NAMESPACE,
            json.dumps(
                [identity_text(v) for v in values], ensure_ascii=False, separators=(",", ":")
            ),
        )
    )


def clean(value):
    """Remove authentication material and duplicated model raw/source envelopes."""
    if isinstance(value, dict):
        return {
            k: clean(v)
            for k, v in value.items()
            if k not in {"raw", "source"}
            and not any(
                secret in k.lower().replace("_", "").replace("-", "") for secret in SECRET_KEYS
            )
        }
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def configuration_hash(configuration):
    def business(value):
        if isinstance(value, dict):
            return {key: business(item) for key, item in value.items() if key not in METADATA}
        if isinstance(value, list):
            return [business(item) for item in value]
        return value

    return hashlib.sha256(canonical(business(configuration)).encode("utf-8")).hexdigest()


def prepare_document(kind, attributes, asset, observed_at):
    document = {key: value for key, value in clean(attributes).items() if value is not None}
    document.update(master_server=asset.hostname, region=asset.region)
    if kind == "images-contents":
        document["created_at"] = timestamp(observed_at)
    else:
        document.update(
            technology=asset.technology,
            collected_at=timestamp(observed_at),
            updated_at=timestamp(observed_at),
        )
        if kind in {"policies", "slps"}:
            document["hash"] = configuration_hash(document["data"])
    identifier = document_id(kind, document)
    canonical(document)  # Reject non-JSON values before entering a Bulk batch.
    return ParsedDocument(identifier=identifier, data=document)
