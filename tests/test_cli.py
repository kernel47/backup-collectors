from backup_collector import cli
from backup_collector.exceptions import ConfigurationError
from backup_collector.result import ExecutionResult


def test_context_is_created_from_cli_arguments():
    args = cli.create_parser().parse_args(
        [
            "collect",
            "netbackup",
            "jobs",
            "--scope",
            "pamela",
            "--asset",
            "master-01",
            "--hours",
            "24",
            "--output",
            "json",
            "--dry-run",
        ]
    )
    context = cli.context_from_args(args)
    assert context.source == "netbackup"
    assert context.data_type == "jobs"
    assert context.scope == "pamela"
    assert context.asset == "master-01"
    assert context.hours == 24
    assert context.output == "json"
    assert context.dry_run is True


def test_cli_success_summary(monkeypatch, capsys):
    result = ExecutionResult("netbackup", "policies", "pamela", 2, 2, 2, "OK", 0.12)
    monkeypatch.setattr(cli, "execute", lambda context, settings: result)
    code = cli.main(["collect", "netbackup", "policies", "--scope", "pamela"])
    assert code == 0
    assert capsys.readouterr().out.startswith("OK - scope=pamela")


def test_expected_error_becomes_icinga_critical(monkeypatch, capsys):
    def fail(context, settings):
        raise ConfigurationError("missing setting")

    monkeypatch.setattr(cli, "execute", fail)
    code = cli.main(["collect", "netbackup", "policies", "--scope", "pamela"])
    assert code == 2
    assert "CRITICAL" in capsys.readouterr().out

