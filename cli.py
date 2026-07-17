import argparse
from datetime import datetime
import sys
from typing import Sequence

from exceptions import BackupCollectorError
from models import CollectionContext, Settings
from services.icinga import configure_logging, handle_error, handle_success, show_progress
from runtime import execute

CLI_EXAMPLES = """Exemples:
  backup-collector collect netbackup --asset master-01 --scope pamela --hours 24
  backup-collector collect netbackup --asset master-01 --scope logstash --hours 24
  backup-collector collect netbackup --asset master-01 --scope baseline
  backup-collector collect datadomain --asset dd-01 --scope baseline
"""


def parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid ISO-8601 datetime: {value}") from exc


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backup-collector",
        description="Collect, parse and send backup asset data.",
        epilog=CLI_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser(
        "collect",
        help="run a collection pipeline",
        description="Run the source workflow selected by the scope for one asset.",
        epilog=CLI_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    collect.add_argument(
        "source",
        choices=["netbackup", "datadomain", "tapelibrary"],
        help="asset collector to use",
    )
    collect.add_argument(
        "--scope",
        required=True,
        choices=["pamela", "logstash", "baseline"],
        help="collection workflow, parser and default destination",
    )

    assets = collect.add_mutually_exclusive_group()
    assets.add_argument(
        "--asset",
        metavar="HOSTNAME",
        help="asset hostname resolved through the external referential",
    )
    assets.add_argument("--all-assets", action="store_true", help="reserved for future use")

    collect.add_argument("--start-time", type=parse_datetime, metavar="ISO_DATETIME")
    collect.add_argument("--end-time", type=parse_datetime, metavar="ISO_DATETIME")
    period = collect.add_mutually_exclusive_group()
    period.add_argument("--hours", type=int, help="collect the last N hours")
    period.add_argument("--days", type=int, help="collect the last N days")

    collect.add_argument(
        "--output",
        choices=["backup_hub", "logstash", "referential", "file", "stdout"],
        help="override the destination selected by the scope",
    )
    collect.add_argument("--dry-run", action="store_true", help="collect and parse without sending")
    collect.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="show progress (enabled automatically in an interactive terminal)",
    )
    collect.add_argument("--verbose", action="store_true", help="enable debug logs")
    return parser


def context_from_args(args: argparse.Namespace) -> CollectionContext:
    return CollectionContext(
        source=args.source,
        data_type="workflow",
        scope=args.scope,
        asset=args.asset,
        all_assets=args.all_assets,
        start_time=args.start_time,
        end_time=args.end_time,
        hours=args.hours,
        days=args.days,
        output=args.output,
        dry_run=args.dry_run,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    settings = Settings.from_env()
    configure_logging(verbose=args.verbose, log_level=settings.log_level)
    context = context_from_args(args)
    pretty = args.progress if args.progress is not None else sys.stdout.isatty()
    try:
        result = execute(
            context,
            settings=settings,
            progress=show_progress if pretty else None,
        )
    except BackupCollectorError as exc:
        return handle_error(context, exc)
    except Exception as exc:  # defensive boundary for Icinga
        return handle_error(context, exc, unexpected=True)
    return handle_success(result, pretty=pretty)


if __name__ == "__main__":
    raise SystemExit(main())
