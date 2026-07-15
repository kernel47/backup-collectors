from time import monotonic
from typing import Any

from context import CollectionContext
from modules.output import OutputService
from result import ExecutionResult
from scopes.baseline.collector import BaselineCollector
from scopes.baseline.parser import parse
from scopes.baseline.rules import evaluate
from settings import Settings


class BaselineScope:
    def __init__(self, settings: Settings) -> None:
        self.collector = BaselineCollector()
        self.output_service = OutputService(settings)

    def execute(self, source: Any, context: CollectionContext) -> ExecutionResult:
        started = monotonic()
        datasets = self.collector.collect(source, context)
        findings = parse(evaluate(datasets))
        sent = 0
        if not context.dry_run:
            sent = self.output_service.send(
                findings,
                context,
                asset=context.asset,
                metadata={"workflow": "baseline"},
            )
        collected_count = sum(len(records) for records in datasets.values())
        return ExecutionResult(
            context.source,
            context.data_type,
            context.scope,
            collected_count,
            len(findings),
            sent,
            "OK",
            monotonic() - started,
        )
