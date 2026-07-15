from time import monotonic
from typing import Any

from context import CollectionContext
from outputs import DEFAULT_OUTPUTS, build_output
from result import ExecutionResult
from scopes.baseline.collector import BaselineCollector
from scopes.baseline.output import send_baseline_result
from scopes.baseline.parser import parse
from scopes.baseline.rules import evaluate
from settings import Settings


class BaselineScope:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.collector = BaselineCollector()

    def execute(self, source: Any, context: CollectionContext) -> ExecutionResult:
        started = monotonic()
        datasets = self.collector.collect(source, context)
        findings = parse(evaluate(datasets))
        sent = 0
        if not context.dry_run:
            name = context.output or DEFAULT_OUTPUTS[context.scope]
            sent = send_baseline_result(
                findings,
                context,
                build_output(name, self.settings),
                context.asset,
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
