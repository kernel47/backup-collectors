from datetime import UTC, datetime


def parse(findings: list[dict]) -> list[dict]:
    evaluated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return [{**finding, "evaluated_at": evaluated_at} for finding in findings]

