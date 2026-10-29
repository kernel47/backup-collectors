"""jobs: source-specific collection with a small explicit execution sequence."""

import math
from datetime import UTC, datetime, timedelta

from collectors.netbackup import client
from collectors.netbackup.client import date_parameters
from collectors.netbackup.parser import parse_job
from core.collection import CollectionRun
from core.models import CollectionContext, CollectionReport, Settings

STANDARD_FILTER = "policyType ne 'VMWARE'"
VMWARE_FILTER = "policyType eq 'VMWARE'"


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
    # Resolve once so both passes use exactly the same window.
    start_date, end_date = job_period(hours=hours, start_date=start_date, end_date=end_date)
    yield from iter_started_jobs(api_client, start_date=start_date, end_date=end_date)
    for job in iter_finished_jobs(api_client, start_date=start_date, end_date=end_date):
        # Already handled by the started pass; no growing set of IDs is needed.
        started = job.start_time
        if isinstance(started, str):
            try:
                started = datetime.fromisoformat(started)
            except ValueError:
                started = None  # Let the parser report this invalid document.
        if (
            isinstance(started, datetime)
            and started.tzinfo is not None
            and start_date <= started <= end_date
        ):
            continue
        yield job


def iter_started_jobs(api_client, *, hours=None, start_date=None, end_date=None):
    """Yield all standard/VMware jobs starting in the requested window."""
    start_date, end_date = job_period(hours=hours, start_date=start_date, end_date=end_date)
    period = date_parameters(start_date=start_date, end_date=end_date)
    yield from api_client.jobs.iter(filter=STANDARD_FILTER, date_field="startTime", **period)
    yield from api_client.jobs.iter(filter=VMWARE_FILTER, date_field="startTime", **period)


def iter_finished_jobs(api_client, *, hours=None, start_date=None, end_date=None):
    """Yield all standard/VMware jobs finishing in the requested window."""
    start_date, end_date = job_period(hours=hours, start_date=start_date, end_date=end_date)
    period = date_parameters(start_date=start_date, end_date=end_date)
    yield from api_client.jobs.iter(filter=STANDARD_FILTER, date_field="endTime", **period)
    yield from api_client.jobs.iter(filter=VMWARE_FILTER, date_field="endTime", **period)


def job_period(*, hours=None, start_date=None, end_date=None):
    if (start_date is None) != (end_date is None):
        raise ValueError("start_date and end_date must be supplied together")
    if start_date is not None:
        if hours is not None:
            raise ValueError("Use hours or start_date/end_date")
        if any(not isinstance(d, datetime) or d.tzinfo is None for d in (start_date, end_date)):
            raise ValueError("Dates require a timezone")
        if start_date >= end_date:
            raise ValueError("start_date must precede end_date")
        return start_date, end_date
    hours = 24 if hours is None else hours
    if isinstance(hours, bool) or not math.isfinite(hours) or hours <= 0:
        raise ValueError("hours must be positive and finite")
    end_date = datetime.now(UTC)
    return end_date - timedelta(hours=hours), end_date
