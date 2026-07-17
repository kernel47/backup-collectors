import cli
from exceptions import ConfigurationError
from models import ExecutionResult


def test_cli_help_contains_examples():
    help_text = cli.create_parser().format_help()
    assert "Exemples:" in help_text
    assert "collect netbackup --asset" in help_text


def test_context_is_created_from_cli_arguments():
    args = cli.create_parser().parse_args(
        [
            "collect",
            "netbackup",
            "--scope",
            "pamela",
            "--asset",
            "master-01",
            "--hours",
            "24",
            "--output",
            "file",
            "--dry-run",
        ]
    )
    context = cli.context_from_args(args)
    assert context.source == "netbackup"
    assert context.data_type == "workflow"
    assert context.scope == "pamela"
    assert context.asset == "master-01"
    assert context.hours == 24
    assert context.output == "file"
    assert context.dry_run is True


def test_cli_success_summary(monkeypatch, capsys):
    result = ExecutionResult("netbackup", "policies", "pamela", 2, 2, 2, "OK", 0.12)
    monkeypatch.setattr(cli, "execute", lambda context, settings, progress: result)
    code = cli.main(["collect", "netbackup", "--scope", "pamela"])
    assert code == 0
    assert capsys.readouterr().out.startswith("OK - scope=pamela")


def test_expected_error_becomes_icinga_critical(monkeypatch, capsys):
    def fail(context, settings, progress):
        raise ConfigurationError("missing setting")

    monkeypatch.setattr(cli, "execute", fail)
    code = cli.main(["collect", "netbackup", "--scope", "pamela"])
    assert code == 2
    assert "CRITICAL" in capsys.readouterr().out


def test_cli_can_force_pretty_progress(monkeypatch, capsys):
    result = ExecutionResult("netbackup", "policies", "pamela", 2, 2, 2, "OK", 0.12)

    def succeed(context, settings, progress):
        progress("collection_started", data_type="policies", hostname="master-01")
        return result

    monkeypatch.setattr(cli, "execute", succeed)
    code = cli.main(
        ["collect", "netbackup", "--scope", "pamela", "--progress"]
    )

    assert code == 0
    output = capsys.readouterr().out
    assert "Collecte policies sur le serveur master-01" in output
    assert "Collectés : 2 | Parsés : 2 | Envoyés : 2" in output
