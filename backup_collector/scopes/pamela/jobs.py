def parse(records: list[dict]) -> list[dict]:
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

