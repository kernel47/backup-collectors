from types import SimpleNamespace

from models import CollectionContext
from modules.netbackup import collect


class Model:
    def __init__(self, value):
        self.value = value

    def model_dump(self, mode):
        assert mode == "json"
        return {"value": self.value}


class Service:
    def list(self, **kwargs):
        return [Model(kwargs)]

    def clients(self):
        return [Model("client-01")]


def client():
    service = Service()
    return SimpleNamespace(
        config=SimpleNamespace(master="master-01"),
        policies=service,
        jobs=service,
        images=service,
    )


def test_collect_policies_through_nbu_service():
    result = collect(
        client(), "policies", CollectionContext("netbackup", "policies", "pamela")
    )
    assert result.asset == "master-01"
    assert result.records == [{"value": {"include_details": True}}]


def test_shares_temporary_adapter_uses_policy_clients():
    result = collect(
        client(), "shares", CollectionContext("netbackup", "shares", "logstash")
    )
    assert result.records == [{"value": "client-01"}]
