from dataclasses import replace
from typing import Any, Callable

from collectors import netbackup
from collectors.pamela import output, parser
from models import Asset, CollectionContext, ScopeResult, Settings

DATA_TYPES = ("policies", "clients", "jobs")


def collect(
    context: CollectionContext,
    settings: Settings,
    asset: Asset | None,
    source_client: Any = None,
    progress: Callable[..., None] | None = None,
) -> ScopeResult:
    result = ScopeResult()
    for data_type in DATA_TYPES:
        step = replace(context, data_type=data_type)
        hostname = asset.hostname if asset else context.asset
        _progress(progress, "collection_started", data_type=data_type, hostname=hostname)
        collected = netbackup.collect(data_type, step, source_client, asset)
        result.collected_count += collected.record_count
        _progress(
            progress,
            "collection_finished",
            data_type=data_type,
            total=collected.record_count,
        )

        _progress(progress, "parsing_started", data_type=data_type, scope="pamela")
        parsed = parser.parse(data_type, collected.records)
        result.parsed_count += len(parsed)
        _progress(progress, "parsing_finished", data_type=data_type, total=len(parsed))

        if not context.dry_run:
            _progress(
                progress,
                "output_started",
                data_type=data_type,
                destination=output.destination(step),
            )
            sent = output.send(parsed, step, settings, collected.asset)
            result.sent_count += sent
            _progress(progress, "output_finished", data_type=data_type, total=sent)

        del collected, parsed

    if context.dry_run:
        _progress(progress, "dry_run")
    return result


def _progress(callback: Callable[..., None] | None, event: str, **details: object) -> None:
    if callback:
        callback(event, **details)
