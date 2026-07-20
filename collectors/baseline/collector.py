from collectors import datadomain, netbackup, tapelibrary
from collectors.baseline import parser
from models import Asset, CollectionContext, ScopeResult, Settings
from services import icinga, output


def collect(
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    show_progress: bool = False,
) -> ScopeResult:
    data_type = "policies" if context.source == "netbackup" else "baseline"
    _progress(
        show_progress,
        "collection_started",
        data_type=data_type,
        hostname=asset.hostname,
    )
    records = _collect_source(data_type, context, asset)
    _progress(
        show_progress,
        "collection_finished",
        data_type=data_type,
        total=len(records),
    )

    _progress(show_progress, "parsing_started", data_type=data_type, scope="baseline")
    parsed = parser.parse(data_type, records, context)
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
            metadata={"workflow": "baseline"},
        )
        _progress(show_progress, "output_finished", data_type=data_type, total=sent)

    result = ScopeResult(len(records), len(parsed), sent)
    icinga.log_collection(
        "baseline", context.source, data_type, len(records), len(parsed), sent
    )
    if context.dry_run:
        _progress(show_progress, "dry_run")
    icinga.log_scope_result("baseline", context.source, result)
    return result


def _collect_source(
    data_type: str,
    context: CollectionContext,
    asset: Asset,
) -> list[dict]:
    if context.source == "netbackup":
        client = netbackup.create_api_client(asset)
        try:
            summaries = netbackup.collect_policies(client)
            return [
                netbackup.collect_policy(client, str(policy.get("name")))
                for policy in summaries
                if policy.get("name")
            ]
        finally:
            client.close()
    if context.source == "datadomain":
        return datadomain.collect(data_type, context, asset)
    return tapelibrary.collect(data_type, context, asset)


def _progress(enabled: bool, event: str, **details: object) -> None:
    if enabled:
        icinga.show_progress(event, **details)
