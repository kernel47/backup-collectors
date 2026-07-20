from dataclasses import replace
from typing import Any, Callable

from collectors import datadomain, netbackup, tapelibrary
from collectors.baseline import output, parser
from models import Asset, CollectionContext, CollectionResult, ScopeResult, Settings


def collect(
    context: CollectionContext,
    settings: Settings,
    asset: Asset | None,
    source_client: Any = None,
    progress: Callable[..., None] | None = None,
) -> ScopeResult:
    result = ScopeResult()
    for data_type in _data_types(context.source):
        step = replace(context, data_type=data_type)
        hostname = asset.hostname if asset else context.asset
        _progress(progress, "collection_started", data_type=data_type, hostname=hostname)
        collected = _collect_source(step, source_client, asset)
        result.collected_count += collected.record_count
        _progress(
            progress,
            "collection_finished",
            data_type=data_type,
            total=collected.record_count,
        )

        _progress(progress, "parsing_started", data_type=data_type, scope="baseline")
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


def _data_types(source: str) -> tuple[str, ...]:
    if source == "netbackup":
        return ("policies",)
    return ("baseline",)


def _collect_source(
    context: CollectionContext,
    source_client: Any,
    asset: Asset | None,
) -> CollectionResult:
    if context.source == "netbackup":
        return netbackup.collect(context.data_type, context, source_client, asset)
    if context.source == "datadomain":
        return datadomain.collect(context.data_type, context, asset)
    return tapelibrary.collect(context.data_type, context, asset)


def _progress(callback: Callable[..., None] | None, event: str, **details: object) -> None:
    if callback:
        callback(event, **details)
