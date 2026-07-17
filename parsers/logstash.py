from datetime import UTC, datetime

from exceptions import ParsingError


def parse(
    data_type: str,
    records: list[dict],
    asset: str | None = None,
) -> list[dict]:
    if data_type not in {"policies", "jobs", "images", "clients"}:
        raise ParsingError(f"Logstash does not support data type: {data_type}")

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
