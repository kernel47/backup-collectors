import argparse
import json
import logging
import sys
from datetime import datetime

from core.models import CollectionContext, CollectionReport
from core.runtime import execute


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parse_datetime(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed
    except ValueError:
        raise argparse.ArgumentTypeError("Expected an ISO-8601 date with timezone") from None


def create_parser():
    parser = Parser(
        prog="backup-collector", description="Collect backup data for one asset", allow_abbrev=False
    )
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect", allow_abbrev=False)
    collect.add_argument(
        "--scope", required=True, choices=["netbackup", "datadomain", "tapelibrary"]
    )
    collect.add_argument(
        "--type",
        required=True,
        choices=["jobs", "policies", "images", "images-contents", "slps"],
    )
    collect.add_argument("--asset", required=True)
    collect.add_argument(
        "--dry-run", action="store_true", help="Print documents without OpenSearch writes"
    )
    collect.add_argument(
        "--debug", action="store_true", help="Log collection stages and Bulk batches to stderr"
    )
    collect.add_argument(
        "--hours", type=float, help="Jobs/images/contents: last N hours (default: 24)"
    )
    collect.add_argument("--start-date", type=parse_datetime)
    collect.add_argument("--end-date", type=parse_datetime)
    return parser


def main(argv=None):
    args = None
    try:
        args = create_parser().parse_args(argv)
        logging.basicConfig(stream=sys.stderr, format="%(levelname)s %(message)s")
        result = execute(
            CollectionContext(**{k: v for k, v in vars(args).items() if k != "command"})
        )
    except ValueError as exc:
        result = CollectionReport()
        result.add_error("cli", "invalid_arguments")
        print(str(exc), file=sys.stderr)
    print(
        json.dumps(result.to_dict(), ensure_ascii=False),
        file=sys.stderr if args and args.dry_run else sys.stdout,
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
