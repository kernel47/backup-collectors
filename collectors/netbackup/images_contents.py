"""images-contents: source-specific collection with a small explicit execution sequence."""

import logging

from collectors.netbackup import client
from collectors.netbackup.client import date_parameters
from collectors.netbackup.parser import parse_image_content
from core.collection import CollectionRun
from core.exceptions import ConfigurationError, ParsingError
from core.models import CollectionContext, CollectionReport, Settings

LOGGER = logging.getLogger(__name__)


def collect_images_contents(
    context: CollectionContext, settings: Settings | None = None
) -> CollectionReport:
    run = CollectionRun(context, settings)
    with run:
        run.prepare()
        run.resolve_asset()
        if not run.asset.is_naas:
            run.report.skip("asset_not_naas")
            LOGGER.debug("skipped asset=%s reason=asset_not_naas", run.asset.hostname)
            return run.report
        run.open_clients(client)
        run.open_output()
        for record in iter_images_contents(
            run.api_client,
            run.ssh_client,
            hours=context.hours,
            start_date=context.start_date,
            end_date=context.end_date,
        ):
            run.process(record, parser=parse_image_content)
            del record
        run.completed = True
    return run.report


def iter_images_contents(
    api_client, ssh_client=None, *, hours=None, start_date=None, end_date=None
):
    if ssh_client is None:
        raise ConfigurationError("Image contents collection requires SSH")
    images = api_client.images.iter(
        **date_parameters(hours=hours, start_date=start_date, end_date=end_date)
    )
    for image in images:
        if not isinstance(image.image_id, str) or not image.image_id.strip():
            raise ParsingError("Image contents require a nonempty image_id")
        if image.backup_time is None:
            raise ParsingError("Image contents require the image backup_time")
        paths = ssh_client.get_image_contents(image.image_id)
        if paths is None or isinstance(paths, (str, bytes, dict)):
            raise ParsingError("get_image_contents must return an iterable of paths")
        for path in paths:
            if not isinstance(path, str) or not path.strip():
                raise ParsingError("Image contents path must be a nonempty string")
            yield {"image_id": image.image_id, "backup_time": image.backup_time, "path": path}
        del paths, image
