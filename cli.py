import argparse
from datetime import datetime
import logging
from typing import Sequence

from context import CollectionContext
from exceptions import BackupCollectorError
from result import ExecutionResult
from runtime.executor import execute
from settings import Settings

ICINGA_CODES = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "UNKNOWN": 3}


def _datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid ISO-8601 datetime: {value}") from exc


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backup-collector")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect", help="run a collection pipeline")
    collect.add_argument("source")
    collect.add_argument("data_type")
    collect.add_argument("--scope", required=True)
    assets = collect.add_mutually_exclusive_group()
    assets.add_argument(
        "--asset",
        metavar="MASTER_SERVER",
        help="master server hostname passed to the external source module",
    )
    assets.add_argument("--all-assets", action="store_true")
    collect.add_argument("--start-time", type=_datetime)
    collect.add_argument("--end-time", type=_datetime)
    period = collect.add_mutually_exclusive_group()
    period.add_argument("--hours", type=int)
    period.add_argument("--days", type=int)
    collect.add_argument(
        "--output", choices=["backup_hub", "logstash", "reference", "json", "stdout"]
    )
    collect.add_argument("--dry-run", action="store_true")
    collect.add_argument("--verbose", action="store_true")
    return parser


def context_from_args(args: argparse.Namespace) -> CollectionContext:
    return CollectionContext(
        source=args.source,
        data_type=args.data_type,
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


def _summary(result: ExecutionResult) -> str:
    return (
        f"{result.status} - scope={result.scope} source={result.source} "
        f"data={result.data_type} collected={result.collected_count} "
        f"parsed={result.parsed_count} sent={result.sent_count} "
        f"duration={result.duration_seconds:.1f}s"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    settings = Settings.from_env()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else getattr(logging, settings.log_level.upper(), 30),
        format="%(levelname)s %(message)s",
    )
    context = context_from_args(args)
    try:
        result = execute(context, settings=settings)
    except BackupCollectorError as exc:
        print(
            f'CRITICAL - scope={context.scope} source={context.source} '
            f'data={context.data_type} error="{exc}"'
        )
        return ICINGA_CODES["CRITICAL"]
    except Exception as exc:  # defensive boundary for Icinga
        logging.exception("Unexpected backup collector error")
        print(
            f'UNKNOWN - scope={context.scope} source={context.source} '
            f'data={context.data_type} error="{exc}"'
        )
        return ICINGA_CODES["UNKNOWN"]
    print(_summary(result))
    return ICINGA_CODES.get(result.status, ICINGA_CODES["UNKNOWN"])


if __name__ == "__main__":
    raise SystemExit(main())
