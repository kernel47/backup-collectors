from datetime import UTC, datetime


def parse(records: list[dict]) -> list[dict]:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return [
        {
            **record,
            "@timestamp": record.get("updated_at") or timestamp,
            "source": {
                "type": "netbackup",
                "asset": record.get("master") or record.get("asset"),
            },
            "data": {"type": "policies"},
        }
        for record in records
    ]

