from exceptions import ParsingError
from models import CollectionContext
from services import record_filters


def parse(
    data_type: str,
    records: list[dict],
    context: CollectionContext,
) -> list[dict]:
    if data_type == "policies":
        records = record_filters.policies(
            records,
            types=context.policy_types,
            names=context.policy_names,
        )
        return [
            {
                "master": record.get("master") or record.get("asset"),
                "policy_name": record.get("policy_name") or record.get("name"),
                "policy_type": record.get("policy_type"),
                "active": record.get("active"),
            }
            for record in records
        ]
    if data_type == "clients":
        return [
            {
                "master": record.get("master") or record.get("asset"),
                "client_name": record.get("client_name") or record.get("name"),
                "os": record.get("os"),
                "hardware": record.get("hardware"),
                "policies": record.get("policies", []),
                "active": record.get("active"),
                "last_backup_status": record.get("last_backup_status"),
            }
            for record in records
        ]
    if data_type == "jobs":
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
                "master": record.get("master") or record.get("asset"),
                "job_id": record.get("job_id") or record.get("id"),
                "policy_name": record.get("policy_name") or record.get("policy"),
                "client_name": record.get("client_name") or record.get("client"),
                "status": record.get("status"),
                "start_time": record.get("start_time"),
                "end_time": record.get("end_time"),
            }
            for record in records
        ]
    raise ParsingError(f"Pamela does not support data type: {data_type}")
