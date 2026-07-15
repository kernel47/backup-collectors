def parse(records: list[dict]) -> list[dict]:
    return [
        {
            "master": record.get("master") or record.get("asset"),
            "policy_name": record.get("policy_name") or record.get("name"),
            "policy_type": record.get("policy_type"),
            "active": record.get("active"),
        }
        for record in records
    ]

