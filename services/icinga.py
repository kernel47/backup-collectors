"""Icinga output, exit codes, and logging in one editable file."""

import logging

from models import CollectionContext, ExecutionResult

EXIT_CODES = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "UNKNOWN": 3}
LOGGER = logging.getLogger(__name__)

PROGRESS_MESSAGES = {
    "asset_lookup_started": lambda data: f"Recherche de l'asset {data['hostname']} dans le référentiel",
    "asset_lookup_finished": lambda data: f"Asset {data['hostname']} chargé",
    "collection_started": lambda data: (
        f"Collecte {data['data_type']} sur le serveur {data['hostname']}"
    ),
    "collection_finished": lambda data: (
        f"{data['total']} {data['data_type']} collecté(s)"
    ),
    "parsing_started": lambda data: (
        f"Parsing {data['data_type']} pour le scope {data['scope']}"
    ),
    "parsing_finished": lambda data: f"{data['total']} {data['data_type']} parsé(s)",
    "output_started": lambda data: (
        f"Envoi {data['data_type']} vers {data['destination']}"
    ),
    "output_finished": lambda data: f"{data['total']} {data['data_type']} envoyé(s)",
    "dry_run": lambda data: "Mode dry-run : aucun envoi",
}

FINISHED_EVENTS = {
    "asset_lookup_finished",
    "collection_finished",
    "parsing_finished",
    "output_finished",
    "dry_run",
}


def configure_logging(verbose: bool = False, log_level: str = "WARNING") -> None:
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.WARNING)
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def show_progress(event: str, **details: object) -> None:
    message_builder = PROGRESS_MESSAGES.get(event)
    if not message_builder:
        return
    icon = "✓" if event in FINISHED_EVENTS else "…"
    print(f"  {icon} {message_builder(details)}", flush=True)


def handle_success(result: ExecutionResult, *, pretty: bool = False) -> int:
    status = result.status if result.status in EXIT_CODES else "UNKNOWN"
    log_summary = (
        f"status={status} scope={result.scope} source={result.source} "
        f"data={result.data_type} total_collected={result.collected_count} "
        f"total_parsed={result.parsed_count} total_sent={result.sent_count} "
        f"duration_seconds={result.duration_seconds:.1f}"
    )
    LOGGER.info("collection_finished %s", log_summary)
    if pretty:
        print(
            f"\n✓ Collecte terminée — {status}\n"
            f"  Collectés : {result.collected_count} | "
            f"Parsés : {result.parsed_count} | Envoyés : {result.sent_count}\n"
            f"  Durée : {result.duration_seconds:.1f}s"
        )
    else:
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
    status = "UNKNOWN" if unexpected else "CRITICAL"
    if unexpected:
        logging.getLogger(__name__).debug("Unexpected backup collector error", exc_info=True)
    message = str(error).replace("\n", " ").replace('"', "'")
    print(
        f"{status} - scope={context.scope} source={context.source} "
        f'data={context.data_type} error="{message}"'
    )
    return EXIT_CODES[status]
