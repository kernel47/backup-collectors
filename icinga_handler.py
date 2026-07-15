"""Single editable boundary for Icinga output, exit codes, and logging."""

import logging

from context import CollectionContext
from result import ExecutionResult

EXIT_CODES = {
    "OK": 0,
    "WARNING": 1,
    "CRITICAL": 2,
    "UNKNOWN": 3,
}

LOG_FORMAT = "%(levelname)s %(message)s"
DEFAULT_LOG_LEVEL = "WARNING"


def configure_logging(verbose: bool = False, log_level: str = DEFAULT_LOG_LEVEL) -> None:
    """Configure every log emitted while Backup Collector runs under Icinga."""
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.WARNING)
    logging.basicConfig(level=level, format=LOG_FORMAT)


def handle_success(result: ExecutionResult) -> int:
    """Print the single Icinga success/warning line and return its exit code."""
    status = result.status if result.status in EXIT_CODES else "UNKNOWN"
    print(
        f"{status} - scope={result.scope} source={result.source} "
        f"data={result.data_type} collected={result.collected_count} "
        f"parsed={result.parsed_count} sent={result.sent_count} "
        f"duration={result.duration_seconds:.1f}s"
    )
    return EXIT_CODES[status]


def handle_error(
    context: CollectionContext,
    error: Exception,
    *,
    unexpected: bool = False,
) -> int:
    """Print one Icinga error line and return CRITICAL or UNKNOWN."""
    status = "UNKNOWN" if unexpected else "CRITICAL"
    if unexpected:
        logging.getLogger(__name__).debug("Unexpected backup collector error", exc_info=True)
    message = str(error).replace("\n", " ").replace('"', "'")
    print(
        f"{status} - scope={context.scope} source={context.source} "
        f'data={context.data_type} error="{message}"'
    )
    return EXIT_CODES[status]
