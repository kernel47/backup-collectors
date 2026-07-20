from dataclasses import replace

from models import CollectionContext, Settings
from services import output as output_service


def send(
    records: list[dict],
    context: CollectionContext,
    settings: Settings,
    asset: str,
) -> int:
    destination = context.output or "logstash"
    return output_service.send(
        records,
        replace(context, output=destination),
        settings,
        asset=asset,
    )


def destination(context: CollectionContext) -> str:
    return context.output or "logstash"
