from collectors.baseline import parser
from models import Asset, CollectionContext, CollectionResult, ScopeResult, Settings
from services import datadomain, icinga, netbackup, output, tapelibrary


def collect(
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    show_progress: bool = False,
) -> ScopeResult:
    result = ScopeResult()
    hostname = asset.hostname

    for data_type in _data_types(context.source):
        _progress(show_progress, "collection_started", data_type=data_type, hostname=hostname)
        collected = _collect_source(data_type, context, asset)
        result.collected_count += collected.record_count
        _progress(
            show_progress,
            "collection_finished",
            data_type=data_type,
            total=collected.record_count,
        )

        _progress(show_progress, "parsing_started", data_type=data_type, scope="baseline")
        parsed = parser.parse(data_type, collected.records)
        result.parsed_count += len(parsed)
        _progress(show_progress, "parsing_finished", data_type=data_type, total=len(parsed))

        sent = 0
        if not context.dry_run:
            _progress(
                show_progress,
                "output_started",
                data_type=data_type,
                destination=output.destination_for(context),
            )
            sent = output.send(
                parsed,
                context,
                settings,
                data_type=data_type,
                asset=collected.asset,
                metadata={"workflow": "baseline"},
            )
            result.sent_count += sent
            _progress(show_progress, "output_finished", data_type=data_type, total=sent)

        icinga.log_collection(
            "baseline",
            context.source,
            data_type,
            collected.record_count,
            len(parsed),
            sent,
        )

        del collected, parsed

    if context.dry_run:
        _progress(show_progress, "dry_run")
    icinga.log_scope_result("baseline", context.source, result)
    return result


def _data_types(source: str) -> tuple[str, ...]:
    if source == "netbackup":
        return ("policies",)
    return ("baseline",)


def _collect_source(
    data_type: str,
    context: CollectionContext,
    asset: Asset,
) -> CollectionResult:
    if context.source == "netbackup":
        return netbackup.collect(data_type, context, asset)
    if context.source == "datadomain":
        return datadomain.collect(data_type, context, asset)
    return tapelibrary.collect(data_type, context, asset)


def _progress(enabled: bool, event: str, **details: object) -> None:
    if enabled:
        icinga.show_progress(event, **details)
