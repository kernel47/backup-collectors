from typing import Sequence

from cli_helper import context_from_args, create_parser
from exceptions import BackupCollectorError
from modules.icinga import configure_logging, handle_error, handle_success
from runtime import execute
from settings import Settings


def main(argv: Sequence[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    settings = Settings.from_env()
    configure_logging(verbose=args.verbose, log_level=settings.log_level)
    context = context_from_args(args)
    try:
        result = execute(context, settings=settings)
    except BackupCollectorError as exc:
        return handle_error(context, exc)
    except Exception as exc:  # defensive boundary for Icinga
        return handle_error(context, exc, unexpected=True)
    return handle_success(result)


if __name__ == "__main__":
    raise SystemExit(main())
