from collectors.logstash import parser
from models import Asset, CollectionContext, ScopeResult, Settings
from services import icinga, netbackup, output

DATA_TYPES = ("jobs", "policies", "images")


def collect(
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    show_progress: bool = False,
) -> ScopeResult:
    result = ScopeResult()
    hostname = asset.hostname

    for data_type in DATA_TYPES:
        _progress(show_progress, "collection_started", data_type=data_type, hostname=hostname)
        collected = netbackup.collect(data_type, context, asset)
        result.collected_count += collected.record_count
        _progress(
            show_progress,
            "collection_finished",
            data_type=data_type,
            total=collected.record_count,
        )

        _progress(show_progress, "parsing_started", data_type=data_type, scope="logstash")
        parsed = parser.parse(data_type, collected.records, collected.asset)
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
            )
            result.sent_count += sent
            _progress(show_progress, "output_finished", data_type=data_type, total=sent)

        icinga.log_collection(
            "logstash",
            context.source,
            data_type,
            collected.record_count,
            len(parsed),
            sent,
        )

        del collected, parsed

    if context.dry_run:
        _progress(show_progress, "dry_run")
    icinga.log_scope_result("logstash", context.source, result)
    return result


def _progress(enabled: bool, event: str, **details: object) -> None:
    if enabled:
        icinga.show_progress(event, **details)
