"""Select the attributes needed from each NetBackup object."""

from nbu.parsers.policies import parse_policy_detail

from core.exceptions import ParsingError
from services.documents import identity_text, timestamp


def _attributes(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    raise ParsingError("Expected a NetBackup object or dictionary")


def _text(value):
    if value is not None and not isinstance(value, str):
        raise ParsingError("Expected a string")
    return value


def _keyword(value):
    return str(value) if value is not None else None


def _date(value):
    return timestamp(value) if value is not None else None


def _name(value):
    value = _text(value)
    if value is None or not value.strip():
        raise ParsingError("Missing or empty identity")
    return value


def parse_job(job):
    job = _attributes(job)
    job_id = identity_text(job.get("job_id"))
    if job_id.isdecimal():
        job_id = str(int(job_id))
    if job.get("start_time") is None:
        raise ParsingError("Job start_time is required")
    return {
        "job_id": job_id,
        "parent_job_id": _keyword(job.get("parent_job_id")),
        "type": _text(job.get("type")),
        "state": _name(job.get("state")),
        "status": _keyword(job.get("status")),
        "policy": _text(job.get("policy")),
        "client": _text(job.get("client")),
        "schedule": _text(job.get("schedule")),
        "storage_unit": _text(job.get("storage_unit")),
        "backup_id": _text(job.get("backup_id")),
        "start_time": _date(job.get("start_time")),
        "end_time": _date(job.get("end_time")),
        "elapsed_seconds": job.get("elapsed_seconds"),
        "kilobytes": job.get("kilobytes"),
        "files": job.get("files"),
        "percent_complete": job.get("percent_complete"),
        "data": {"status_description": job.get("status_description")},
    }


def parse_policy(policy):
    policy = _attributes(policy)
    if policy.get("raw"):
        # Keep the policy's own configuration instead of derived SLP values.
        own = parse_policy_detail(policy["raw"]).model_dump(mode="json")
        own["clients"] = policy.get("clients", own["clients"])
        policy = own
    clients = policy.get("clients", [])
    if not isinstance(clients, list):
        raise ParsingError("clients must be a list of names")
    for name in clients:
        _name(name)
    result = {
        "name": _name(policy.get("name")),
        "policy_type": _text(policy.get("policy_type")),
        "slp": _text(policy.get("slp")),
        "storage": _text(policy.get("storage")),
        "clients": clients,
        "active": policy.get("active"),
        "storage_is_slp": policy.get("storage_is_slp"),
    }
    result["data"] = {
        **result,
        "schedules": policy.get("schedules", []),
        "backup_selections": policy.get("backup_selections", []),
        "retention": policy.get("retention"),
    }
    if policy.get("raw"):
        result["data"]["configuration"] = policy["raw"]
    return result


def parse_image(image):
    image = _attributes(image)
    return {
        "image_id": _name(image.get("image_id")),
        "backup_id": _text(image.get("backup_id")),
        "client": _text(image.get("client")),
        "policy": _text(image.get("policy")),
        "policy_type": _text(image.get("policy_type")),
        "schedule": _text(image.get("schedule")),
        "schedule_type": _text(image.get("schedule_type")),
        "retention_level": _keyword(image.get("retention_level")),
        "storage_location": _text(image.get("storage_location")),
        "backup_time": _date(image.get("backup_time")),
        "expiration_time": _date(image.get("expiration_time")),
        "copy_number": image.get("copy_number"),
        "kilobytes": image.get("kilobytes"),
        "data": {},
    }


def parse_slp(slp):
    slp = _attributes(slp)
    result = {
        "name": _name(slp.get("name")),
        "status": slp.get("status"),
        "target_storage": _text(slp.get("target_storage")),
        "active": slp.get("active"),
    }
    result["data"] = {
        **result,
        "operations": slp.get("operations", []),
        "retention": slp.get("retention"),
    }
    result["status"] = _keyword(result["status"])
    if slp.get("raw"):
        result["data"]["configuration"] = slp["raw"]
    return result


def parse_image_content(content):
    content = _attributes(content)
    if content.get("backup_time") is None:
        raise ParsingError("Image contents backup_time is required")
    return {
        "image_id": _name(content.get("image_id")),
        "path": _name(content.get("path")),
        "backup_time": _date(content.get("backup_time")),
    }
