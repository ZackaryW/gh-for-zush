import subprocess

from gh_for_zush import entrypoint


def test_extract_dry_run_flag_removes_flag() -> None:
    dry_run, argv = entrypoint.extract_dry_run_flag(["--dry-run", "self", "install", "jobqueue"])

    assert dry_run is True
    assert argv == ["self", "install", "jobqueue"]


def test_extract_dry_run_flag_keeps_other_args() -> None:
    dry_run, argv = entrypoint.extract_dry_run_flag(["self", "available"])

    assert dry_run is False
    assert argv == ["self", "available"]


def test_dry_run_executor_echoes_command() -> None:
    result = entrypoint.dry_run_execute_command("pip install git+https://github.com/ZackaryW/zush_jobqueue.git")

    assert result.returncode == 0
    assert result.stdout == "pip install git+https://github.com/ZackaryW/zush_jobqueue.git\n"
