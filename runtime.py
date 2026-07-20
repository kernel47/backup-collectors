from time import monotonic

from collectors.baseline import collector as baseline
from collectors.logstash import collector as logstash
from collectors.pamela import collector as pamela
from exceptions import UnsupportedCollectionError
from models import Asset, CollectionContext, ExecutionResult, ScopeResult, Settings
from services import icinga, referential


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
    show_progress: bool = False,
) -> ExecutionResult:
    validate_context(context)
    settings = settings or Settings.from_env()
    started = monotonic()

    asset = _resolve_asset(context, settings, show_progress)
    scope_result = _run_scope(context, settings, asset, show_progress)
    return ExecutionResult(
        source=context.source,
        scope=context.scope,
        collected_count=scope_result.collected_count,
        parsed_count=scope_result.parsed_count,
        sent_count=scope_result.sent_count,
        status="OK",
        duration_seconds=monotonic() - started,
    )


def _resolve_asset(
    context: CollectionContext,
    settings: Settings,
    show_progress: bool,
) -> Asset:
    if show_progress:
        icinga.show_progress("asset_lookup_started", hostname=context.asset)
    asset = referential.get_asset(context.asset, settings)
    if show_progress:
        icinga.show_progress("asset_lookup_finished", hostname=asset.hostname)
    return asset


def _run_scope(
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    show_progress: bool,
) -> ScopeResult:
    if context.scope == "pamela":
        return pamela.collect(context, settings, asset, show_progress)
    if context.scope == "logstash":
        return logstash.collect(context, settings, asset, show_progress)
    return baseline.collect(context, settings, asset, show_progress)
