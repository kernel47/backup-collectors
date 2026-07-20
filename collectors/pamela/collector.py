from collectors import netbackup
from collectors.pamela import parser
from models import Asset, CollectionContext, ScopeResult, Settings
from services import icinga, output


def collect(
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    show_progress: bool = False,
) -> ScopeResult:
    result = ScopeResult()
    client = netbackup.create_api_client(asset)
    try:
        _collect_policies(client, context, settings, asset, result, show_progress)
        _collect_jobs(client, context, settings, asset, result, show_progress)
    finally:
        client.close()

    if context.dry_run:
        _progress(show_progress, "dry_run")
    icinga.log_scope_result("pamela", context.source, result)
    return result


def _collect_policies(
    client,
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    result: ScopeResult,
    show_progress: bool,
) -> None:
    _progress(show_progress, "collection_started", data_type="policies", hostname=asset.hostname)
    policies = netbackup.collect_policies(client)
    result.collected_count += len(policies)
    _progress(
        show_progress,
        "collection_finished",
        data_type="policies",
        total=len(policies),
    )

    selected = parser.filter_policies(policies, context)
    _progress(show_progress, "policy_clients_started", total=len(selected))
    detailed = []
    for policy in selected:
        policy_name = policy.get("name") or policy.get("policy_name")
        if policy_name:
            details = netbackup.collect_policy(client, str(policy_name))
            detailed.append({**policy, **details})
    client_count = sum(len(policy.get("clients", [])) for policy in detailed)
    _progress(show_progress, "policy_clients_finished", total=client_count)

    _progress(show_progress, "parsing_started", data_type="policies", scope="pamela")
    parsed = parser.parse_policies(detailed, asset.hostname)
    result.parsed_count += len(parsed)
    _progress(show_progress, "parsing_finished", data_type="policies", total=len(parsed))
    sent = _send(parsed, "policies", context, settings, asset, show_progress)
    result.sent_count += sent
    icinga.log_collection(
        "pamela", context.source, "policies", len(policies), len(parsed), sent
    )


def _collect_jobs(
    client,
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    result: ScopeResult,
    show_progress: bool,
) -> None:
    _progress(show_progress, "collection_started", data_type="jobs", hostname=asset.hostname)
    jobs = netbackup.collect_jobs(client, context)
    result.collected_count += len(jobs)
    _progress(show_progress, "collection_finished", data_type="jobs", total=len(jobs))

    _progress(show_progress, "parsing_started", data_type="jobs", scope="pamela")
    parsed = parser.parse_jobs(jobs, context, asset.hostname)
    result.parsed_count += len(parsed)
    _progress(show_progress, "parsing_finished", data_type="jobs", total=len(parsed))
    sent = _send(parsed, "jobs", context, settings, asset, show_progress)
    result.sent_count += sent
    icinga.log_collection("pamela", context.source, "jobs", len(jobs), len(parsed), sent)


def _send(
    records: list[dict],
    data_type: str,
    context: CollectionContext,
    settings: Settings,
    asset: Asset,
    show_progress: bool,
) -> int:
    if context.dry_run:
        return 0
    _progress(
        show_progress,
        "output_started",
        data_type=data_type,
        destination=output.destination_for(context),
    )
    sent = output.send(
        records,
        context,
        settings,
        data_type=data_type,
        asset=asset.hostname,
    )
    _progress(show_progress, "output_finished", data_type=data_type, total=sent)
    return sent


def _progress(enabled: bool, event: str, **details: object) -> None:
    if enabled:
        icinga.show_progress(event, **details)
