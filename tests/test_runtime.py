import sys
from types import ModuleType, SimpleNamespace

import pytest

from exceptions import CollectionError, ConfigurationError, UnsupportedCollectionError
from models import CollectionContext, Settings
from modules.netbackup import create_client
from runtime import execute, validate_context


class FakePolicies:
    def list(self, **kwargs):
        return [{"name": "daily", "policy_type": "Standard", "active": True}]

    def clients(self):
        return []


class FakeClient:
    config = SimpleNamespace(master="master-01")
    policies = FakePolicies()


def test_unsupported_collection_is_rejected():
    context = CollectionContext("netbackup", "images", "pamela")
    with pytest.raises(UnsupportedCollectionError, match="data_type=images"):
        validate_context(context)


def test_datadomain_command_reaches_placeholder_module():
    context = CollectionContext("datadomain", "future", "pamela")
    with pytest.raises(CollectionError, match="not implemented"):
        execute(context, settings=Settings())


def test_supported_netbackup_command_is_accepted():
    validate_context(CollectionContext("netbackup", "images", "logstash"))


def test_file_output_override_avoids_http(tmp_path):
    context = CollectionContext("netbackup", "policies", "pamela", output="file")
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
    client = create_client("master-01")
    assert isinstance(client, FakeNetBackup)
    assert created == {"master": "master-01"}


def test_nbu_client_requires_master_server_hostname():
    with pytest.raises(ConfigurationError, match="--asset MASTER_SERVER"):
        create_client("")
