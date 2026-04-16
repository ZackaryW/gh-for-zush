"""Dry-run helpers shared by the gh-for-zush repository entrypoint."""

from __future__ import annotations

import subprocess


def extract_dry_run_flag(argv: list[str]) -> tuple[bool, list[str]]:
    """Return whether dry-run mode was requested and the argv with that flag removed."""
    filtered_argv: list[str] = []
    dry_run = False
    for argument in argv:
        if argument == "--dry-run":
            dry_run = True
            continue
        filtered_argv.append(argument)
    return dry_run, filtered_argv


def dry_run_execute_command(command: str) -> subprocess.CompletedProcess[str]:
    """Return one successful fake process that echoes the rendered command for testing."""
    return subprocess.CompletedProcess(command, 0, stdout=f"{command}\n", stderr="")
