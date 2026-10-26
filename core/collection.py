"""Reusable execution tools; resource files keep their own collection sequence."""

import json
import logging
import resource
import sys
import tracemalloc
from contextlib import ExitStack, redirect_stdout
from datetime import UTC, datetime
from time import monotonic

from core.exceptions import BackupCollectorError, ConfigurationError, ParsingError
from core.models import CollectionContext, CollectionReport, PerformanceStats, Settings
from services import opensearch, referencial
from services.documents import prepare_document

LOGGER = logging.getLogger(__name__)


class CollectionRun:
    def __init__(self, context: CollectionContext, settings: Settings | None = None):
        self.context, self.settings = context, settings
        self.report = CollectionReport.from_context(context)
        self.asset = self.api_client = self.ssh_client = self.writer = None
        self.stage, self.completed = "configuration", False
        self.storage_error = False
        self.resources = ExitStack()
        self.profiler = DebugProfiler() if context.debug else None

    def __enter__(self):
        self.started, self.console = monotonic(), sys.stdout
        if self.profiler is not None:
            self.profiler.start()
        self.resources.enter_context(redirect_stdout(sys.stderr))
        return self

    def __exit__(self, exc_type, error, traceback):
        if error is not None:
            self.record_error(self.stage, error)
        self.flush()
        try:
            self.resources.close()
        except Exception as exc:  # noqa: BLE001 - cleanup failures must be reported
            self.record_error("cleanup", exc)
        duration = monotonic() - self.started
        if self.profiler is not None:
            self.report.performance = self.profiler.finish(duration)
            self.profiler.log(self.report.performance, duration)
        self.report.finish(self.completed, duration)
        LOGGER.debug(
            "finished status=%s collected=%d confirmed=%d duration=%.3fs",
            self.report.status,
            self.report.collection.collected,
            self.report.storage.confirmed,
            self.report.duration_seconds,
        )
        return error is not None and isinstance(error, Exception)

    def prepare(self):
        if self.context.debug:
            logging.basicConfig(stream=sys.stderr, format="%(levelname)s %(name)s %(message)s")
        for name in ("core", "collectors", "services"):
            logging.getLogger(name).setLevel(
                logging.DEBUG if self.context.debug else logging.INFO
            )
        self.settings = self.settings or Settings.from_env()
        if not self.context.debug:
            for name in ("core", "collectors", "services"):
                logging.getLogger(name).setLevel(self.settings.log_level.upper())
        LOGGER.debug(
            "start scope=%s type=%s hours=%s start_date=%s end_date=%s",
            self.context.scope,
            self.context.type,
            self.context.hours,
            self.context.start_date,
            self.context.end_date,
        )

    def resolve_asset(self):
        self.stage = "referencial"
        LOGGER.debug("resolving asset")
        self.asset = referencial.get_asset(self.context.asset, self.settings)
        self.report.master_server = self.asset.hostname
        self.report.region = self.asset.region
        self.report.technology = self.asset.technology

    def open_clients(self, clients):
        self.stage = "collection"
        if self.asset.api:
            self.api_client = clients.create_api_client(self.asset, self.settings)
            self.resources.callback(self.api_client.close)
        if self.api_client is None:
            raise ConfigurationError("NetBackup API is required for this collection type")
        self.ssh_client = clients.create_ssh_client(self.asset)
        if self.ssh_client is not None:
            self.resources.callback(self.ssh_client.close)
        LOGGER.debug(
            "clients initialized; api=%s ssh=%s",
            self.api_client is not None,
            self.ssh_client is not None,
        )

    def open_output(self, *, configuration=False):
        self.stage = "storage"
        if not self.context.dry_run:
            sink = opensearch.create_client(self.settings)
            self.resources.callback(sink.close)
            limit = self.settings.opensearch_batch_size
            if configuration:
                limit = min(limit, self.settings.opensearch_configuration_batch_size)
            self.writer = opensearch.BulkWriter(
                sink, self.settings, self.report.storage, self.report.errors, batch_size=limit
            )
        self.stage = "collection"

    def process(self, record, parser):
        """Verify/parse one object, then immediately hand it to the bounded sink."""
        self.report.collection.collected += 1
        if self.report.collection.collected == 1 or self.report.collection.collected % 1000 == 0:
            LOGGER.debug("received=%d", self.report.collection.collected)
        document = self.parse(record, parser)
        if document is not None:
            self.send(document)

    def parse(self, record, parser):
        try:
            attributes = parser(record)
            return prepare_document(self.context.type, attributes, self.asset, datetime.now(UTC))
        except (ParsingError, ValueError, TypeError, KeyError) as error:
            self.report.collection.invalid += 1
            self.record_error("normalization", error)
            return None

    def send(self, document):
        self.stage = "storage"
        identifier, data = document.identifier, document.data
        if self.writer is not None:
            self.writer.add(
                opensearch.operation(self.context.type, identifier, data, self.settings)
            )
        else:
            print(
                json.dumps({"_id": identifier, "document": data}, ensure_ascii=False),
                file=self.console,
                flush=True,
            )
            self.report.storage.displayed += 1
        self.stage = "collection"

    def flush(self):
        try:
            if self.writer is not None:
                self.writer.flush()
        except Exception as error:  # noqa: BLE001 - never confirm an unacknowledged batch
            self.record_error("storage", error)
        if self.stage == "storage" or self.storage_error:
            valid = self.report.collection.collected - self.report.collection.invalid
            self.report.storage.failed = max(
                self.report.storage.failed, valid - self.report.storage.confirmed
            )

    def record_error(self, stage, error):
        if stage == "storage":
            self.storage_error = True
        message = str(error) if isinstance(error, BackupCollectorError) else None
        self.report.add_error(stage, type(error).__name__, message)
        if self.context.debug:
            LOGGER.debug(
                "error stage=%s code=%s", stage, type(error).__name__,
                exc_info=(type(error), error, error.__traceback__),
            )


class DebugProfiler:
    """Process CPU deltas, run-local Python allocations and process-lifetime RSS peak."""

    def start(self):
        self.cpu_start = resource.getrusage(resource.RUSAGE_SELF)
        self.owns_trace = not tracemalloc.is_tracing()
        if self.owns_trace:
            tracemalloc.start()

    def finish(self, duration):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        user = usage.ru_utime - self.cpu_start.ru_utime
        system = usage.ru_stime - self.cpu_start.ru_stime
        peak = None
        if self.owns_trace:
            try:
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
        # getrusage returns bytes on macOS and KiB on Linux/RHEL.
        rss = int(usage.ru_maxrss * (1 if sys.platform == "darwin" else 1024))
        return PerformanceStats(
            cpu_user_seconds=round(user, 6),
            cpu_system_seconds=round(system, 6),
            cpu_total_seconds=round(user + system, 6),
            cpu_average_percent=round(100 * (user + system) / duration, 2) if duration else 0,
            python_peak_bytes=peak,
            process_peak_rss_bytes=rss,
        )

    @staticmethod
    def log(stats, duration):
        python_peak = (
            f"{stats.python_peak_bytes / 1024**2:.2f} MiB"
            if stats.python_peak_bytes is not None
            else "unavailable (existing trace)"
        )
        LOGGER.debug(
            "performance wall=%.3fs cpu=%.3fs (user=%.3fs system=%.3fs) cpu_average=%.2f%% "
            "python_peak=%s process_lifetime_peak_rss=%.2f MiB",
            duration,
            stats.cpu_total_seconds,
            stats.cpu_user_seconds,
            stats.cpu_system_seconds,
            stats.cpu_average_percent,
            python_peak,
            stats.process_peak_rss_bytes / 1024**2,
        )
