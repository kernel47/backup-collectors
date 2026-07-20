from collectors.baseline.parser import parse as parse_baseline
from collectors.logstash.parser import parse as parse_logstash
from collectors.pamela.parser import parse as parse_pamela


def test_pamela_policy_parser_selects_expected_fields():
    parsed = parse_pamela(
        "policies",
        [{"name": "daily", "policy_type": "Standard", "active": True, "ignored": 1}]
    )
    assert parsed == [
        {
            "master": None,
            "policy_name": "daily",
            "policy_type": "Standard",
            "active": True,
        }
    ]


def test_logstash_policy_parser_enriches_event():
    parsed = parse_logstash("policies", [{"name": "daily", "master": "master-01"}])
    assert parsed[0]["name"] == "daily"
    assert parsed[0]["source"] == {"type": "netbackup", "asset": "master-01"}
    assert parsed[0]["data"] == {"type": "policies"}
    assert "@timestamp" in parsed[0]


def test_pamela_client_parser_selects_expected_fields():
    parsed = parse_pamela(
        "clients",
        [{"name": "client-01", "os": "Linux", "policies": ["daily"], "ignored": 1}],
    )
    assert parsed == [
        {
            "master": None,
            "client_name": "client-01",
            "os": "Linux",
            "hardware": None,
            "policies": ["daily"],
            "active": None,
            "last_backup_status": None,
        }
    ]


def test_baseline_policy_parser_creates_finding():
    parsed = parse_baseline("policies", [{"name": "daily", "clients": []}])
    assert parsed[0]["rule"] == "EXAMPLE_POLICY_WITHOUT_CLIENT"
