import json

from context import CollectionContext
from modules.output import OutputService
from settings import Settings


def test_file_output_is_atomic_and_has_metadata(tmp_path):
    context = CollectionContext(
        "netbackup", "policies", "pamela", asset="master-emea-01", output="file"
    )
    count = OutputService(Settings(output_dir=tmp_path)).send([{"name": "daily"}], context)
    files = list(tmp_path.rglob("*.json"))
    assert count == 1
    assert len(files) == 1
    assert not list(tmp_path.rglob("*.tmp"))
    document = json.loads(files[0].read_text())
    assert document["metadata"]["record_count"] == 1
    assert document["metadata"]["asset"] == "master-emea-01"
    assert document["records"] == [{"name": "daily"}]


def test_referential_output_is_selected_by_parameter(monkeypatch):
    sent = {}

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        sent["url"] = url
        sent["payload"] = kwargs["json"]
        return Response()

    monkeypatch.setattr("modules.output.http.httpx.post", fake_post)
    context = CollectionContext("netbackup", "baseline", "baseline", output="referential")
    count = OutputService(
        Settings(referential_url="https://referential.example.test")
    ).send([{"rule": "example"}], context)
    assert count == 1
    assert sent["url"] == "https://referential.example.test"
    assert sent["payload"]["metadata"]["destination"] == "referential"


def test_scope_selects_logstash_by_default(monkeypatch):
    sent = {}

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        sent["url"] = url
        sent["payload"] = kwargs["json"]
        return Response()

    monkeypatch.setattr("modules.output.http.httpx.post", fake_post)
    context = CollectionContext("netbackup", "jobs", "logstash")
    count = OutputService(Settings(logstash_url="https://logstash.example.test")).send(
        [{"job_id": 42}], context
    )
    assert count == 1
    assert sent["url"] == "https://logstash.example.test"
    assert sent["payload"]["metadata"]["destination"] == "logstash"
