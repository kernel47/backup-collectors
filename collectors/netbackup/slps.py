"""slps: source-specific collection with a small explicit execution sequence."""

from collectors.netbackup import client
from collectors.netbackup.parser import parse_slp
from core.collection import CollectionRun
from core.models import CollectionContext, CollectionReport, Settings


def collect_slps(context: CollectionContext, settings: Settings | None = None) -> CollectionReport:
    run = CollectionRun(context, settings)
    with run:
        run.prepare()
        run.resolve_asset()
        run.open_clients(client)
        run.open_output(configuration=True)
        for record in iter_slps(run.api_client, run.ssh_client):
            run.process(record, parser=parse_slp)
            del record
        run.completed = True
    return run.report


def iter_slps(api_client, ssh_client=None):
    for summary in api_client.slp.list():
        yield api_client.slp.get(summary.name)
