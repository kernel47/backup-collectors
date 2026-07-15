import json

from context import CollectionContext
from outputs.json_file import JsonFileOutput


def test_json_output_is_atomic_and_has_metadata(tmp_path):
    context = CollectionContext(
        "netbackup", "policies", "pamela", asset="master-emea-01"
    )
    count = JsonFileOutput(tmp_path).send([{"name": "daily"}], context)
    files = list(tmp_path.rglob("*.json"))
    assert count == 1
    assert len(files) == 1
    assert not list(tmp_path.rglob("*.tmp"))
    document = json.loads(files[0].read_text())
    assert document["metadata"]["record_count"] == 1
    assert document["metadata"]["asset"] == "master-emea-01"
    assert document["records"] == [{"name": "daily"}]
