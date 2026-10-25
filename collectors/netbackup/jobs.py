"""jobs: source-specific collection with a small explicit execution sequence."""

from datetime import UTC, datetime, timedelta

from collectors.netbackup import client
from collectors.netbackup.client import date_parameters
from collectors.netbackup.parser import parse_job
from core.collection import CollectionRun
from core.models import CollectionContext, CollectionReport, Settings


def collect_jobs(context: CollectionContext, settings: Settings | None = None) -> CollectionReport:
    run = CollectionRun(context, settings)
    with run:
        run.prepare()
        run.resolve_asset()
        run.open_clients(client)
        run.open_output()
        for record in iter_jobs(
            run.api_client,
            run.ssh_client,
            hours=context.hours,
            start_date=context.start_date,
            end_date=context.end_date,
        ):
            run.process(record, parser=parse_job)
            del record
        run.completed = True
    return run.report


def iter_jobs(api_client, ssh_client=None, *, hours=None, start_date=None, end_date=None):
    # Freeze the requested period before fetching the first page.
    if start_date is None:
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(hours=24 if hours is None else hours)
    yield from api_client.jobs.iter(**date_parameters(start_date=start_date, end_date=end_date))
