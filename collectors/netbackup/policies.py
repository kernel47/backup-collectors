"""policies: source-specific collection with a small explicit execution sequence."""

import logging

from collectors.netbackup import client
from collectors.netbackup.parser import parse_policy
from core.collection import CollectionRun
from core.exceptions import ConfigurationError, ParsingError
from core.models import CollectionContext, CollectionReport, Settings

# Exact policy types, compared without case sensitivity.
EXCLUDE_TYPES: list[str] = []
# Fragments of policy names, compared without case sensitivity.
EXCLUDE_NAMES: list[str] = []

LOGGER = logging.getLogger(__name__)


def collect_policies(
    context: CollectionContext, settings: Settings | None = None
) -> CollectionReport:
    run = CollectionRun(context, settings)
    with run:
        run.prepare()
        run.resolve_asset()
        run.open_clients(client)
        run.open_output(configuration=True)
        for record in iter_policies(run.api_client, run.ssh_client, run.report.collection):
            run.process(record, parser=parse_policy)
            del record
        run.completed = True
    return run.report


def iter_policies(api_client, ssh_client=None, stats=None):
    summaries = api_client.policies.list(include_details=False)
    for summary in summaries:
        if policy_excluded(summary):
            if stats is not None:
                stats.excluded += 1
            LOGGER.debug(
                "policy excluded name=%s type=%s",
                summary.name,
                getattr(summary, "policy_type", None),
            )
            continue
        if ssh_client is None:
            raise ConfigurationError("Policy collection requires SSH to retrieve clients")
        policy = api_client.policies.get(summary.name)
        enrich_policy_clients(policy, ssh_client)
        yield policy
        del policy


def enrich_policy_clients(policy, ssh_client):
    clients = ssh_client.get_policy_clients(policy.name)
    if not isinstance(clients, list) or any(
        not isinstance(name, str) or not name.strip() for name in clients
    ):
        raise ParsingError("get_policy_clients must return a list of client names")
    policy.clients = clients


def policy_excluded(policy):
    policy_type = str(getattr(policy, "policy_type", None) or "").casefold()
    name = policy.name.casefold()
    return any(policy_type == value.casefold() for value in EXCLUDE_TYPES) or any(
        fragment.casefold() in name for fragment in EXCLUDE_NAMES if fragment
    )
