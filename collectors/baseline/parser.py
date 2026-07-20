from datetime import UTC, datetime

from models import CollectionContext
from services import record_filters


def parse(data_type: str, records: list[dict], context: CollectionContext) -> list[dict]:
    if data_type != "policies":
        return records

    records = record_filters.policies(
        records,
        types=context.policy_types,
        names=context.policy_names,
    )
    evaluated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    findings = []
    for policy in records:
        name = policy.get("name") or policy.get("policy_name")
        if policy.get("active") is False:
            findings.append(
                {
                    "rule": "EXAMPLE_POLICY_DISABLED",
                    "severity": "warning",
                    "policy": name,
                    "evaluated_at": evaluated_at,
                }
            )
        if not policy.get("clients"):
            findings.append(
                {
                    "rule": "EXAMPLE_POLICY_WITHOUT_CLIENT",
                    "severity": "warning",
                    "policy": name,
                    "evaluated_at": evaluated_at,
                }
            )
    return findings
