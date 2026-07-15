def evaluate(datasets: dict[str, list[dict]]) -> list[dict]:
    """Example rules only; production baseline rules will replace or extend these."""
    findings = []
    for policy in datasets.get("policies", []):
        name = policy.get("name") or policy.get("policy_name")
        if policy.get("active") is False:
            findings.append(
                {"rule": "EXAMPLE_POLICY_DISABLED", "severity": "warning", "policy": name}
            )
        if not policy.get("clients"):
            findings.append(
                {"rule": "EXAMPLE_POLICY_WITHOUT_CLIENT", "severity": "warning", "policy": name}
            )
    return findings

