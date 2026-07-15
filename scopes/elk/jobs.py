from scopes.elk.policies import parse as _parse


def parse(records: list[dict]) -> list[dict]:
    parsed = _parse(records)
    for record in parsed:
        record["data"]["type"] = "jobs"
        record["@timestamp"] = record.get("start_time") or record["@timestamp"]
    return parsed

