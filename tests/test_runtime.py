import logging
import sys
from types import ModuleType

import pytest

from exceptions import CollectionError, ConfigurationError, UnsupportedCollectionError
from models import Asset, CollectionContext, CollectionResult, Settings
from runtime import execute, validate_context
from services.netbackup import create_client


def fake_netbackup_collect(data_type, context, asset):
    records = {
        "policies": [{"name": "daily", "policy_type": "Standard", "active": True}],
        "clients": [{"name": "client-01", "os": "Linux", "policies": ["daily"]}],
        "jobs": [{"job_id": 42, "client_name": "client-01", "status": 0}],
        "images": [{"backup_id": "client-01_42"}],
    }[data_type]
    return CollectionResult(asset.hostname, records)


@pytest.fixture(autouse=True)
def resolve_asset(monkeypatch):
    monkeypatch.setattr(
        "runtime.referential.get_asset",
        lambda hostname, settings: Asset(hostname=hostname, api=True),
    )


def test_unsupported_collection_is_rejected():
    context = CollectionContext("datadomain", "pamela", "dd-01")
    with pytest.raises(UnsupportedCollectionError, match="source=datadomain scope=pamela"):
        validate_context(context)


def test_datadomain_command_reaches_placeholder_service():
    context = CollectionContext("datadomain", "baseline", "dd-01")
    with pytest.raises(CollectionError, match="not implemented"):
        execute(context, settings=Settings())


def test_supported_netbackup_command_is_accepted():
    validate_context(CollectionContext("netbackup", "logstash", "master-01"))


def test_file_output_override_avoids_http(monkeypatch, tmp_path):
    monkeypatch.setattr("collectors.pamela.collector.netbackup.collect", fake_netbackup_collect)
    context = CollectionContext("netbackup", "pamela", "master-01", output="file")
    result = execute(context, settings=Settings(output_dir=tmp_path))

    assert result.sent_count == 3
    files = list(tmp_path.rglob("*.json"))
    assert len(files) == 3
    assert all('"asset": "master-01"' in file.read_text() for file in files)


def test_pamela_sends_and_logs_each_collection_before_the_next(monkeypatch, caplog):
    monkeypatch.setattr("collectors.pamela.collector.netbackup.collect", fake_netbackup_collect)
    sent_types = []

    def fake_send(records, context, settings, *, data_type, asset, metadata=None):
        sent_types.append(data_type)
        return len(records)

    monkeypatch.setattr("collectors.pamela.collector.output.send", fake_send)
    with caplog.at_level(logging.INFO, logger="services.icinga"):
        result = execute(CollectionContext("netbackup", "pamela", "master-01"), Settings())

    assert sent_types == ["policies", "clients", "jobs"]
    assert result.collected_count == 3
    assert result.parsed_count == 3
    assert result.sent_count == 3
    assert "data=policies collected=1 parsed=1 sent=1" in caplog.text
    assert "data=clients collected=1 parsed=1 sent=1" in caplog.text
    assert "data=jobs collected=1 parsed=1 sent=1" in caplog.text


def test_runtime_resolves_asset_and_scope_reports_progress(monkeypatch):
    calls = []
    events = []

    def fake_get_asset(hostname, settings):
        calls.append((hostname, settings))
        return Asset(hostname=hostname, api=True)

    monkeypatch.setattr("runtime.referential.get_asset", fake_get_asset)
    monkeypatch.setattr("collectors.pamela.collector.netbackup.collect", fake_netbackup_collect)
    monkeypatch.setattr(
        "services.icinga.show_progress",
        lambda event, **details: events.append((event, details)),
    )
    settings = Settings()
    context = CollectionContext("netbackup", "pamela", "master-01", dry_run=True)
    result = execute(context, settings=settings, show_progress=True)

    assert calls == [("master-01", settings)]
    assert result.sent_count == 0
    assert [details["data_type"] for event, details in events if event == "collection_started"] == [
        "policies",
        "clients",
        "jobs",
    ]
    assert result.collected_count == 3
    assert events[-1] == ("dry_run", {})


def test_nbu_package_client_is_used(monkeypatch):
    created = {}

    class FakeNetBackup:
        def __init__(self, **kwargs):
            created.update(kwargs)

    module = ModuleType("nbu")
    module.NetBackup = FakeNetBackup
    monkeypatch.setitem(sys.modules, "nbu", module)
    asset = Asset(
        hostname="master-01",
        api_username="api-user",
        api_password="api-secret",
        domain_type="unixpwd",
        domain_name="master-01",
        version="11.0",
        api=True,
    )
    client = create_client(asset)
    assert isinstance(client, FakeNetBackup)
    assert created == {
        "master": "master-01",
        "username": "api-user",
        "password": "api-secret",
        "domain_type": "unixpwd",
        "domain_name": "master-01",
        "version": "11.0",
    }


def test_nbu_client_rejects_asset_without_api():
    with pytest.raises(ConfigurationError, match="API is disabled"):
        create_client(Asset(hostname="master-01", api=False))
