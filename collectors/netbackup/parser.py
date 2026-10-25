"""Select the attributes needed from each NetBackup object."""

from nbu.parsers.policies import parse_policy_detail

from core.exceptions import ParsingError


def _attributes(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    raise ParsingError("Expected a NetBackup object or dictionary")


def parse_job(job):
    job = _attributes(job)
    return {
        "job_id": job.get("job_id"),
        "parent_job_id": job.get("parent_job_id"),
        "type": job.get("type"),
        "state": job.get("state"),
        "status": job.get("status"),
        "policy": job.get("policy"),
        "client": job.get("client"),
        "schedule": job.get("schedule"),
        "storage_unit": job.get("storage_unit"),
        "backup_id": job.get("backup_id"),
        "start_time": job.get("start_time"),
        "end_time": job.get("end_time"),
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
    result = {
        "name": policy.get("name"),
        "policy_type": policy.get("policy_type"),
        "slp": policy.get("slp"),
        "storage": policy.get("storage"),
        "clients": policy.get("clients", []),
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
        "image_id": image.get("image_id"),
        "backup_id": image.get("backup_id"),
        "client": image.get("client"),
        "policy": image.get("policy"),
        "policy_type": image.get("policy_type"),
        "schedule": image.get("schedule"),
        "schedule_type": image.get("schedule_type"),
        "retention_level": image.get("retention_level"),
        "storage_location": image.get("storage_location"),
        "backup_time": image.get("backup_time"),
        "expiration_time": image.get("expiration_time"),
        "copy_number": image.get("copy_number"),
        "kilobytes": image.get("kilobytes"),
        "data": {},
    }


def parse_slp(slp):
    slp = _attributes(slp)
    result = {
        "name": slp.get("name"),
        "status": slp.get("status"),
        "target_storage": slp.get("target_storage"),
        "active": slp.get("active"),
    }
    result["data"] = {
        **result,
        "operations": slp.get("operations", []),
        "retention": slp.get("retention"),
    }
    if slp.get("raw"):
        result["data"]["configuration"] = slp["raw"]
    return result


def parse_image_content(content):
    content = _attributes(content)
    return {
        "image_id": content.get("image_id"),
        "path": content.get("path"),
        "backup_time": content.get("backup_time"),
    }
