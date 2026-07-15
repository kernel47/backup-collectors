from time import monotonic
from typing import Any

from backup_collector.context import CollectionContext
from backup_collector.exceptions import ParsingError
from backup_collector.outputs import DEFAULT_OUTPUTS, build_output
from backup_collector.result import ExecutionResult
from backup_collector.scopes.pamela import jobs, policies
from backup_collector.scopes.pamela.output import send_pamela_result
from backup_collector.settings import Settings

PARSERS = {"policies": policies.parse, "jobs": jobs.parse}


class PamelaScope:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, source: Any, context: CollectionContext) -> ExecutionResult:
        started = monotonic()
        collected = source.collect(context.data_type, context)
        try:
            parsed = PARSERS[context.data_type](collected.records)
        except (KeyError, TypeError, ValueError) as exc:
            raise ParsingError(f"Pamela parsing failed: {exc}") from exc
        sent = 0
        if not context.dry_run:
            name = context.output or DEFAULT_OUTPUTS[context.scope]
            sent = send_pamela_result(
                parsed, context, build_output(name, self.settings), collected.asset
            )
        return ExecutionResult(
            context.source,
            context.data_type,
            context.scope,
            collected.record_count,
            len(parsed),
            sent,
            "OK",
            monotonic() - started,
        )
