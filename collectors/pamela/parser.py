from models import CollectionContext
from services import record_filters


def filter_policies(records: list[dict], context: CollectionContext) -> list[dict]:
    return record_filters.policies(
        records,
        types=context.policy_types,
        names=context.policy_names,
    )


def parse_policies(records: list[dict], hostname: str) -> list[dict]:
    return [
        {
            "master": hostname,
            "policy_name": record.get("policy_name") or record.get("name"),
            "policy_type": record.get("policy_type"),
            "active": record.get("active"),
            "clients": record.get("clients", []),
            "schedules": record.get("schedules", []),
            "backup_selections": record.get("backup_selections", []),
            "retention": record.get("retention"),
            "storage": record.get("storage"),
            "slp": record.get("slp"),
        }
        for record in records
    ]


def parse_jobs(
    records: list[dict],
    context: CollectionContext,
    hostname: str,
) -> list[dict]:
    records = record_filters.dates(
        records,
        fields=("start_time", "startTime", "end_time", "endTime"),
        start=context.start_time,
        end=context.end_time,
        hours=context.hours,
        days=context.days,
    )
    return [
        {
            "master": hostname,
            "job_id": record.get("job_id") or record.get("id"),
            "policy_name": record.get("policy_name") or record.get("policy"),
            "client_name": record.get("client_name") or record.get("client"),
            "status": record.get("status"),
            "start_time": record.get("start_time"),
            "end_time": record.get("end_time"),
        }
        for record in records
    ]
