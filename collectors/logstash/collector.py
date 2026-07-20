from collectors import netbackup
from collectors.logstash import parser
from models import Asset, CollectionContext, ScopeResult, Settings
from services import icinga, output

DATA_TYPES = ("jobs", "policies", "images")


def collect(
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    show_progress: bool = False,
) -> ScopeResult:
    result = ScopeResult()
    client = netbackup.create_api_client(asset)
    try:
        for data_type in DATA_TYPES:
            _progress(
                show_progress,
                "collection_started",
                data_type=data_type,
                hostname=asset.hostname,
            )
            records = _collect(client, data_type, context)
            result.collected_count += len(records)
            _progress(
                show_progress,
                "collection_finished",
                data_type=data_type,
                total=len(records),
            )

            _progress(show_progress, "parsing_started", data_type=data_type, scope="logstash")
            parsed = parser.parse(data_type, records, context, asset.hostname)
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
                    asset=asset.hostname,
                )
                result.sent_count += sent
                _progress(show_progress, "output_finished", data_type=data_type, total=sent)

            icinga.log_collection(
                "logstash", context.source, data_type, len(records), len(parsed), sent
            )
            del records, parsed
    finally:
        client.close()

    if context.dry_run:
        _progress(show_progress, "dry_run")
    icinga.log_scope_result("logstash", context.source, result)
    return result


def _collect(client, data_type: str, context: CollectionContext) -> list[dict]:
    if data_type == "jobs":
        return netbackup.collect_jobs(client, context)
    if data_type == "policies":
        return netbackup.collect_policies(client)
    return netbackup.collect_images(client, context)


def _progress(enabled: bool, event: str, **details: object) -> None:
    if enabled:
        icinga.show_progress(event, **details)
