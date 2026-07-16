from modules.icinga import handle_error, handle_success
from models import CollectionContext, ExecutionResult


def test_warning_output_and_exit_code(capsys):
    result = ExecutionResult("netbackup", "jobs", "pamela", 3, 3, 2, "WARNING", 1.25)
    assert handle_success(result) == 1
    assert capsys.readouterr().out == (
        "WARNING - scope=pamela source=netbackup data=jobs "
        "collected=3 parsed=3 sent=2 duration=1.2s\n"
    )


def test_error_is_kept_on_one_icinga_line(capsys):
    context = CollectionContext("netbackup", "jobs", "pamela")
    assert handle_error(context, RuntimeError('line 1\n"line 2"')) == 2
    output = capsys.readouterr().out
    assert output.count("\n") == 1
    assert output.startswith("CRITICAL - scope=pamela")
