from models import CollectionContext
from parsers.logstash import parse as parse_logstash
from parsers.pamela import parse as parse_pamela
from parsers.service import parse_for_scope


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


def test_parser_service_selects_parser_from_scope():
    context = CollectionContext("netbackup", "policies", "pamela")
    parsed = parse_for_scope(context, [{"name": "daily"}], "master-01")
    assert parsed[0]["policy_name"] == "daily"
