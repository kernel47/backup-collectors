"""images: source-specific collection with a small explicit execution sequence."""

from collectors.netbackup import client
from collectors.netbackup.client import date_parameters
from collectors.netbackup.parser import parse_image
from core.collection import CollectionRun
from core.models import CollectionContext, CollectionReport, Settings


def collect_images(
    context: CollectionContext, settings: Settings | None = None
) -> CollectionReport:
    run = CollectionRun(context, settings)
    with run:
        run.prepare()
        run.resolve_asset()
        run.open_clients(client)
        run.open_output()
        for record in iter_images(
            run.api_client,
            run.ssh_client,
            hours=context.hours,
            start_date=context.start_date,
            end_date=context.end_date,
        ):
            run.process(record, parser=parse_image)
            del record
        run.completed = True
    return run.report


def iter_images(api_client, ssh_client=None, *, hours=None, start_date=None, end_date=None):
    yield from api_client.images.iter(
        **date_parameters(hours=hours, start_date=start_date, end_date=end_date)
    )
