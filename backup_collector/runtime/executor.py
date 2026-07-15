from typing import Any

from backup_collector.context import CollectionContext
from backup_collector.exceptions import ConfigurationError, UnsupportedCollectionError
from backup_collector.result import ExecutionResult
from backup_collector.runtime.registry import SCOPES, SOURCES, SUPPORTED_COLLECTIONS
from backup_collector.settings import Settings


def validate_context(context: CollectionContext) -> None:
    supported = SUPPORTED_COLLECTIONS.get(context.scope, {}).get(context.source, set())
    if context.data_type not in supported:
        raise UnsupportedCollectionError(
            "Unsupported collection: "
            f"source={context.source} data_type={context.data_type} scope={context.scope}"
        )


def _netbackup_client(context: CollectionContext, settings: Settings) -> Any:
    settings.require_netbackup(context.asset)
    try:
        from nbu import NetBackup
    except ImportError as exc:
        raise ConfigurationError("The netbackup-py package is not installed") from exc
    return NetBackup(
        master=context.asset or settings.nbu_host,
        username=settings.nbu_username,
        password=settings.nbu_password,
        verify_ssl=settings.nbu_verify_tls,
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
        client = _netbackup_client(context, settings)
    source = source_class(client)
    scope = scope_class(settings)
    try:
        return scope.execute(source=source, context=context)
    finally:
        if owns_client and hasattr(client, "close"):
            client.close()

