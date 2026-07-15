from time import monotonic
from typing import Any

from context import CollectionContext
from exceptions import ParsingError
from modules.output import OutputService
from result import ExecutionResult
from scopes.logstash import images, jobs, policies, shares
from settings import Settings

PARSERS = {
    "policies": policies.parse,
    "jobs": jobs.parse,
    "images": images.parse,
    "shares": shares.parse,
}


class LogstashScope:
    def __init__(self, settings: Settings) -> None:
        self.output_service = OutputService(settings)

    def execute(self, source: Any, context: CollectionContext) -> ExecutionResult:
        started = monotonic()
        collected = source.collect(context.data_type, context)
        try:
            parsed = PARSERS[context.data_type](collected.records)
        except (KeyError, TypeError, ValueError) as exc:
            raise ParsingError(f"Logstash parsing failed: {exc}") from exc
        for record in parsed:
            record["source"]["asset"] = record["source"].get("asset") or collected.asset
        sent = 0
        if not context.dry_run:
            sent = self.output_service.send(parsed, context, asset=collected.asset)
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
