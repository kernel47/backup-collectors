from dataclasses import replace
from time import monotonic
from typing import Any, Callable

from collectors import datadomain, netbackup, tapelibrary
from exceptions import UnsupportedCollectionError
from models import Asset, CollectionContext, CollectionResult, ExecutionResult, Settings
from parsers.service import parse_for_scope
from services import output, referential

ProgressCallback = Callable[..., None]

WORKFLOWS = {
    ("netbackup", "pamela"): ("policies", "clients", "jobs"),
    ("netbackup", "logstash"): ("jobs", "policies", "images"),
    ("netbackup", "baseline"): ("policies",),
    ("datadomain", "baseline"): ("baseline",),
    ("tapelibrary", "baseline"): ("baseline",),
}


def workflow_for(context: CollectionContext) -> tuple[str, ...]:
    workflow = WORKFLOWS.get((context.source, context.scope))
    if workflow:
        return workflow
    raise UnsupportedCollectionError(
        f"Unsupported workflow: source={context.source} scope={context.scope}"
    )


def validate_context(context: CollectionContext) -> None:
    workflow_for(context)


def execute(
    context: CollectionContext,
    settings: Settings | None = None,
    source_client: Any = None,
    progress: ProgressCallback | None = None,
) -> ExecutionResult:
    workflow = workflow_for(context)
    settings = settings or Settings.from_env()
    started = monotonic()

    if context.asset:
        _progress(progress, "asset_lookup_started", hostname=context.asset)
        asset = referential.get_asset(context.asset, settings)
        _progress(progress, "asset_lookup_finished", hostname=asset.hostname)
    else:
        asset = None

    collected_total = 0
    parsed_total = 0
    sent_total = 0

    for data_type in workflow:
        step_context = replace(context, data_type=data_type)
        hostname = asset.hostname if asset else context.asset
        _progress(
            progress,
            "collection_started",
            data_type=data_type,
            hostname=hostname,
        )
        collected = _collect(step_context, source_client, asset)
        collected_total += collected.record_count
        _progress(
            progress,
            "collection_finished",
            data_type=data_type,
            total=collected.record_count,
        )

        _progress(progress, "parsing_started", data_type=data_type, scope=context.scope)
        parsed = parse_for_scope(step_context, collected.records, collected.asset)
        parsed_total += len(parsed)
        _progress(progress, "parsing_finished", data_type=data_type, total=len(parsed))

        if not context.dry_run:
            destination = output.destination_for(step_context)
            _progress(
                progress,
                "output_started",
                data_type=data_type,
                destination=destination,
            )
            metadata = {"workflow": "baseline"} if context.scope == "baseline" else None
            sent = output.send(
                parsed,
                step_context,
                settings,
                asset=collected.asset,
                metadata=metadata,
            )
            sent_total += sent
            _progress(progress, "output_finished", data_type=data_type, total=sent)

        # Only totals survive this iteration; the next collection does not retain
        # records from the previous one.
        del collected, parsed

    if context.dry_run:
        _progress(progress, "dry_run")

    return ExecutionResult(
        source=context.source,
        data_type="workflow",
        scope=context.scope,
        collected_count=collected_total,
        parsed_count=parsed_total,
        sent_count=sent_total,
        status="OK",
        duration_seconds=monotonic() - started,
    )


def _collect(
    context: CollectionContext,
    source_client: Any,
    asset: Asset | None,
) -> CollectionResult:
    if context.source == "netbackup":
        return netbackup.collect(context.data_type, context, source_client, asset)
    if context.source == "datadomain":
        return datadomain.collect(context.data_type, context, asset)
    return tapelibrary.collect(context.data_type, context, asset)


def _progress(callback: ProgressCallback | None, event: str, **details: Any) -> None:
    if callback:
        callback(event, **details)
