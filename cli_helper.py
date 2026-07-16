"""Argument parsing helpers used by the command-line entry point."""

import argparse
from datetime import datetime

from context import CollectionContext


def parse_datetime(value: str) -> datetime:
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
        help="master server hostname passed to the source module",
    )
    assets.add_argument("--all-assets", action="store_true")

    collect.add_argument("--start-time", type=parse_datetime)
    collect.add_argument("--end-time", type=parse_datetime)
    period = collect.add_mutually_exclusive_group()
    period.add_argument("--hours", type=int)
    period.add_argument("--days", type=int)

    collect.add_argument(
        "--output", choices=["backup_hub", "logstash", "referential", "file", "stdout"]
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

