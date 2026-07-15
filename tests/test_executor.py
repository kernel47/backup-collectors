import sys
from types import ModuleType, SimpleNamespace

import pytest

from context import CollectionContext
from exceptions import UnsupportedCollectionError
from runtime.executor import _netbackup_client, execute, validate_context
from runtime.registry import SCOPES, SOURCES
from scopes.elk import ElkScope
from scopes.pamela import PamelaScope
from settings import Settings
from sources.netbackup import NetBackupSource


class FakePolicies:
    def list(self, **kwargs):
        return [{"name": "daily", "policy_type": "Standard", "active": True}]

    def clients(self):
        return []


class FakeClient:
    config = SimpleNamespace(master="master-01")
    policies = FakePolicies()


def test_unsupported_collection_is_rejected():
    context = CollectionContext("datadomain", "jobs", "pamela")
    with pytest.raises(UnsupportedCollectionError, match="source=datadomain"):
        validate_context(context)


def test_registry_selects_expected_source_and_scopes():
    assert SOURCES["netbackup"] is NetBackupSource
    assert SCOPES["pamela"] is PamelaScope
    assert SCOPES["elk"] is ElkScope


def test_json_output_override_avoids_http(tmp_path):
    context = CollectionContext("netbackup", "policies", "pamela", output="json")
    settings = Settings(output_dir=tmp_path)
    result = execute(context, settings=settings, source_client=FakeClient())
    assert result.sent_count == 1
    files = list(tmp_path.rglob("*.json"))
    assert len(files) == 1
    assert '"asset": "master-01"' in files[0].read_text()


def test_nbu_package_client_is_used(monkeypatch):
    created = {}

    class FakeNetBackup:
        def __init__(self, **kwargs):
            created.update(kwargs)

    module = ModuleType("nbu")
    module.NetBackup = FakeNetBackup
    monkeypatch.setitem(sys.modules, "nbu", module)
    settings = Settings("master-01", "user", "secret", False)
    client = _netbackup_client(CollectionContext("netbackup", "jobs", "pamela"), settings)
    assert isinstance(client, FakeNetBackup)
    assert created == {
        "master": "master-01",
        "username": "user",
        "password": "secret",
        "verify_ssl": False,
    }
