from types import SimpleNamespace

from collectors.netbackup import collect
from models import CollectionContext


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
        "policies", CollectionContext("netbackup", "policies", "pamela"), client()
    )
    assert result.asset == "master-01"
    assert result.records == [{"value": {"include_details": True}}]


def test_clients_collection_uses_policy_clients():
    result = collect(
        "clients", CollectionContext("netbackup", "clients", "pamela"), client()
    )
    assert result.records == [{"value": "client-01"}]
