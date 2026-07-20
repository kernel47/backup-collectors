from time import monotonic
from typing import Any, Callable

from collectors.baseline import collector as baseline
from collectors.logstash import collector as logstash
from collectors.pamela import collector as pamela
from exceptions import UnsupportedCollectionError
from models import Asset, CollectionContext, ExecutionResult, ScopeResult, Settings
from services import referential

ProgressCallback = Callable[..., None]


def validate_context(context: CollectionContext) -> None:
    if context.scope == "pamela" and context.source == "netbackup":
        return
    if context.scope == "logstash" and context.source == "netbackup":
        return
    if context.scope == "baseline" and context.source in {
        "netbackup",
        "datadomain",
        "tapelibrary",
    }:
        return
    raise UnsupportedCollectionError(
        f"Unsupported workflow: source={context.source} scope={context.scope}"
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

    asset = None
    if context.asset:
        _progress(progress, "asset_lookup_started", hostname=context.asset)
        asset = referential.get_asset(context.asset, settings)
        _progress(progress, "asset_lookup_finished", hostname=asset.hostname)

    scope_result = _run_scope(context, settings, asset, source_client, progress)
    return ExecutionResult(
        source=context.source,
        data_type="workflow",
        scope=context.scope,
        collected_count=scope_result.collected_count,
        parsed_count=scope_result.parsed_count,
        sent_count=scope_result.sent_count,
        status="OK",
        duration_seconds=monotonic() - started,
    )


def _run_scope(
    context: CollectionContext,
    settings: Settings,
    asset: Asset | None,
    source_client: Any,
    progress: ProgressCallback | None,
) -> ScopeResult:
    if context.scope == "pamela":
        return pamela.collect(context, settings, asset, source_client, progress)
    if context.scope == "logstash":
        return logstash.collect(context, settings, asset, source_client, progress)
    return baseline.collect(context, settings, asset, source_client, progress)


def _progress(callback: ProgressCallback | None, event: str, **details: Any) -> None:
    if callback:
        callback(event, **details)
