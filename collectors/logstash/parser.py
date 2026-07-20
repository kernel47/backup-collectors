from datetime import UTC, datetime

from exceptions import ParsingError
from models import CollectionContext
from services import record_filters


def parse(
    data_type: str,
    records: list[dict],
    context: CollectionContext,
    asset: str | None = None,
) -> list[dict]:
    if data_type not in {"policies", "jobs", "images"}:
        raise ParsingError(f"Logstash does not support data type: {data_type}")

    if data_type == "policies":
        records = record_filters.policies(
            records,
            types=context.policy_types,
            names=context.policy_names,
        )
    elif data_type == "jobs":
        records = record_filters.dates(
            records,
            fields=("start_time", "startTime", "end_time", "endTime"),
            start=context.start_time,
            end=context.end_time,
            hours=context.hours,
            days=context.days,
        )

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    parsed = []
    for record in records:
        timestamp = record.get("updated_at") or now
        if data_type == "jobs":
            timestamp = record.get("start_time") or timestamp
        elif data_type == "images":
            timestamp = record.get("backup_time") or timestamp
        parsed.append(
            {
                **record,
                "@timestamp": timestamp,
                "source": {
                    "type": "netbackup",
                    "asset": record.get("master") or record.get("asset") or asset,
                },
                "data": {"type": data_type},
            }
        )
    return parsed
