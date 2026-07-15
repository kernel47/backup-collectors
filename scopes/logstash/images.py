from scopes.logstash.policies import parse as _parse


def parse(records: list[dict]) -> list[dict]:
    parsed = _parse(records)
    for record in parsed:
        record["data"]["type"] = "images"
        record["@timestamp"] = record.get("backup_time") or record["@timestamp"]
    return parsed
