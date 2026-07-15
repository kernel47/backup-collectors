from scopes.logstash.policies import parse as parse_logstash_policies
from scopes.pamela.policies import parse as parse_pamela_policies


def test_pamela_policy_parser_selects_expected_fields():
    parsed = parse_pamela_policies(
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
    parsed = parse_logstash_policies([{"name": "daily", "master": "master-01"}])
    assert parsed[0]["name"] == "daily"
    assert parsed[0]["source"] == {"type": "netbackup", "asset": "master-01"}
    assert parsed[0]["data"] == {"type": "policies"}
    assert "@timestamp" in parsed[0]
