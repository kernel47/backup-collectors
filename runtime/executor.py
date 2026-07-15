from typing import Any

from context import CollectionContext
from exceptions import UnsupportedCollectionError
from external.netbackup import create_client as create_netbackup_client
from result import ExecutionResult
from runtime.registry import SCOPES, SOURCES, SUPPORTED_COLLECTIONS
from settings import Settings


def validate_context(context: CollectionContext) -> None:
    supported = SUPPORTED_COLLECTIONS.get(context.scope, {}).get(context.source, set())
    if context.data_type not in supported:
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
    source_class = SOURCES[context.source]
    scope_class = SCOPES[context.scope]

    owns_client = source_client is None and context.source == "netbackup"
    client = source_client
    if context.source == "netbackup" and client is None:
        client = create_netbackup_client(context.asset or "")
    source = source_class(client)
    scope = scope_class(settings)
    try:
        return scope.execute(source=source, context=context)
    finally:
        if owns_client and hasattr(client, "close"):
            client.close()
