from time import monotonic
from typing import Any, Callable

from collectors import datadomain, netbackup, tapelibrary
from exceptions import UnsupportedCollectionError
from models import CollectionContext, ExecutionResult, Settings
from parsers.service import parse_for_scope
from services import output, referential

ProgressCallback = Callable[..., None]


def validate_context(context: CollectionContext) -> None:
    supported = False
    if context.source == "netbackup" and context.scope == "pamela":
        supported = context.data_type in {"policies", "jobs"}
    elif context.source == "netbackup" and context.scope == "logstash":
        supported = context.data_type in {"policies", "jobs", "images", "shares"}
    elif context.source == "netbackup" and context.scope == "baseline":
        supported = context.data_type == "baseline"
    elif context.source in {"datadomain", "tapelibrary"}:
        # The CLI route exists; these collectors will define their data types later.
        supported = True

    if not supported:
        raise UnsupportedCollectionError(
            "Unsupported collection: "
            f"source={context.source} data_type={context.data_type} scope={context.scope}"
        )


def execute(
    context: CollectionContext,
    settings: Settings | None = None,
    source_client: Any = None,
    progress: ProgressCallback | None = None,
) -> ExecutionResult:
    validate_context(context)
    settings = settings or Settings.from_env()
    started = monotonic()

    _progress(progress, "asset_lookup_started", hostname=context.asset)
    asset = referential.get_asset(context.asset, settings) if context.asset else None
    _progress(progress, "asset_lookup_finished", hostname=context.asset)

    collection_type = context.data_type
    if context.source == "netbackup" and context.scope == "baseline":
        collection_type = "policies"
    _progress(
        progress,
        "collection_started",
        data_type=collection_type,
        hostname=asset.hostname if asset else context.asset,
    )
    if context.source == "netbackup":
        collected = netbackup.collect(collection_type, context, source_client, asset)
    elif context.source == "datadomain":
        collected = datadomain.collect(context.data_type, context, asset)
    else:
        collected = tapelibrary.collect(context.data_type, context, asset)
    _progress(progress, "collection_finished", total=collected.record_count)

    _progress(progress, "parsing_started", scope=context.scope)
    parsed = parse_for_scope(context, collected.records, collected.asset)
    _progress(progress, "parsing_finished", total=len(parsed))

    sent = 0
    if not context.dry_run:
        _progress(progress, "output_started", destination=output.destination_for(context))
        metadata = {"workflow": "baseline"} if context.scope == "baseline" else None
        sent = output.send(
            parsed,
            context,
            settings,
            asset=collected.asset,
            metadata=metadata,
        )
        _progress(progress, "output_finished", total=sent)
    else:
        _progress(progress, "dry_run")

    return ExecutionResult(
        source=context.source,
        data_type=context.data_type,
        scope=context.scope,
        collected_count=collected.record_count,
        parsed_count=len(parsed),
        sent_count=sent,
        status="OK",
        duration_seconds=monotonic() - started,
    )


def _progress(callback: ProgressCallback | None, event: str, **details: Any) -> None:
    if callback:
        callback(event, **details)
