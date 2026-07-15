from time import monotonic
from typing import Any

from backup_collector.context import CollectionContext
from backup_collector.outputs import DEFAULT_OUTPUTS, build_output
from backup_collector.result import ExecutionResult
from backup_collector.scopes.baseline.collector import BaselineCollector
from backup_collector.scopes.baseline.output import send_baseline_result
from backup_collector.scopes.baseline.parser import parse
from backup_collector.scopes.baseline.rules import evaluate
from backup_collector.settings import Settings


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
                context.asset or self.settings.nbu_host,
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
