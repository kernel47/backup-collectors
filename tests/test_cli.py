import cli
from models import ExecutionResult


def test_cli_smoke(monkeypatch, capsys):
    captured = {}

    def fake_execute(context, settings, show_progress):
        captured["context"] = context
        captured["progress"] = show_progress
        return ExecutionResult("netbackup", "pamela", 3, 2, 2, "OK", 0.1)

    monkeypatch.setattr(cli, "execute", fake_execute)
    exit_code = cli.main(
        [
            "collect",
            "netbackup",
            "--scope",
            "pamela",
            "--asset",
            "master-01",
            "--hours",
            "24",
            "--policy-type",
            "Standard",
            "--policy-name",
            "PROD-*",
            "--dry-run",
            "--progress",
        ]
    )

    context = captured["context"]
    assert exit_code == 0
    assert context.source == "netbackup"
    assert context.scope == "pamela"
    assert context.asset == "master-01"
    assert context.hours == 24
    assert context.policy_types == ("Standard",)
    assert context.policy_names == ("PROD-*",)
    assert context.dry_run is True
    assert captured["progress"] is True
    assert capsys.readouterr().out.startswith("\n✓ Collecte terminée — OK")
