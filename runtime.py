from time import monotonic
from typing import Any

from context import CollectionContext
from exceptions import UnsupportedCollectionError
from modules import datadomain, netbackup, output, tapelibrary
from parsers.service import parse_for_scope
from result import ExecutionResult
from settings import Settings


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
) -> ExecutionResult:
    validate_context(context)
    settings = settings or Settings.from_env()
    started = monotonic()
    owns_client = False
    client = source_client

    try:
        if context.source == "netbackup":
            if client is None:
                client = netbackup.create_client(context.asset or "")
                owns_client = True
            collection_type = "policies" if context.scope == "baseline" else context.data_type
            collected = netbackup.collect(client, collection_type, context)
        elif context.source == "datadomain":
            collected = datadomain.collect(context.data_type, context)
        else:
            collected = tapelibrary.collect(context.data_type, context)

        parsed = parse_for_scope(context, collected.records, collected.asset)

        sent = 0
        if not context.dry_run:
            metadata = {"workflow": "baseline"} if context.scope == "baseline" else None
            sent = output.send(
                parsed,
                context,
                settings,
                asset=collected.asset,
                metadata=metadata,
            )

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
    finally:
        if owns_client and hasattr(client, "close"):
            client.close()
