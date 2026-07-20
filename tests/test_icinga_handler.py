import logging

from services.icinga import handle_error, handle_success, log_scope_result, show_progress
from models import CollectionContext, ExecutionResult, ScopeResult


def test_warning_output_and_exit_code(capsys):
    result = ExecutionResult("netbackup", "pamela", 3, 3, 2, "WARNING", 1.25)
    assert handle_success(result) == 1
    assert capsys.readouterr().out == (
        "WARNING - scope=pamela source=netbackup "
        "collected=3 parsed=3 sent=2 duration=1.2s\n"
    )


def test_error_is_kept_on_one_icinga_line(capsys):
    context = CollectionContext("netbackup", "pamela", "master-01")
    assert handle_error(context, RuntimeError('line 1\n"line 2"')) == 2
    output = capsys.readouterr().out
    assert output.count("\n") == 1
    assert output.startswith("CRITICAL - scope=pamela")


def test_progress_and_success_log_include_totals(capsys, caplog):
    show_progress("collection_started", data_type="policies", hostname="master-01")
    show_progress("collection_finished", data_type="policies", total=12)
    result = ExecutionResult("netbackup", "pamela", 12, 10, 10, "OK", 1.25)

    with caplog.at_level(logging.INFO, logger="services.icinga"):
        log_scope_result("pamela", "netbackup", ScopeResult(12, 10, 10))
        assert handle_success(result, pretty=True) == 0

    output = capsys.readouterr().out
    assert "Collecte policies sur le serveur master-01" in output
    assert "12 policies collecté(s)" in output
    assert "Collectés : 12 | Parsés : 10 | Envoyés : 10" in output
    assert "scope_report status=OK" in caplog.text
    assert "collected=12 parsed=10 sent=10" in caplog.text
