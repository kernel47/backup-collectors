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
    document.update(master_server=asset.master_server, region=asset.region)
    if kind == "jobs":
        document["job_id"] = identity_text(document.get("job_id"))
        if document["job_id"].isdecimal():
            document["job_id"] = str(int(document["job_id"]))
        if not isinstance(document.get("state"), str) or not document["state"]:
            raise ParsingError("Job state is required")
    for key in ("start_time", "end_time", "backup_time", "expiration_time"):
        if key in document:
            document[key] = timestamp(document[key])
    for key in ("job_id", "parent_job_id", "status", "retention_level"):
        if key in document:
            document[key] = str(document[key])
    for key in ("elapsed_seconds", "kilobytes", "files", "percent_complete", "copy_number"):
        if key in document and (
            isinstance(document[key], bool) or not isinstance(document[key], int)
        ):
            raise ParsingError(f"{key} must be an integer")
    for key in ("active", "storage_is_slp"):
        if key in document and not isinstance(document[key], bool):
            raise ParsingError(f"{key} must be boolean")
    for key in (
        "name",
        "image_id",
        "path",
        "client",
        "policy",
        "policy_type",
        "type",
        "state",
        "schedule",
        "schedule_type",
        "storage_unit",
        "backup_id",
        "storage",
        "slp",
        "target_storage",
        "storage_location",
    ):
        if key in document and not isinstance(document[key], str):
            raise ParsingError(f"{key} must be a string")
    if "clients" in document and (
        not isinstance(document["clients"], list)
        or any(not isinstance(name, str) or not name.strip() for name in document["clients"])
    ):
        raise ParsingError("clients must be a list of nonempty names")
    if kind == "images-contents":
        if "backup_time" not in document:
            raise ParsingError("Image contents backup_time is required")
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
