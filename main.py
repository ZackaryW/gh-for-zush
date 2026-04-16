"""Repository-level entrypoint for running the GitHub-backed zush wrapper."""

from __future__ import annotations
from pathlib import Path

import sys

from zush.core import default_storage
from zush.configparse import load_config

from gh_for_zush import GhConfig, create_ghzush_group
from gh_for_zush.entrypoint import dry_run_execute_command, extract_dry_run_flag


def main(argv: list[str] | None = None) -> None:
    """Run the host-side zush wrapper from the repository root entrypoint."""
    dry_run, click_argv = extract_dry_run_flag(list(sys.argv[1:] if argv is None else argv))
    gh_config = GhConfig(
        allowed_owners=("ZackaryW", "Pathverse")
    )
    config = load_config(
        default_storage()
    )
    if "pvt_" not in config.env_prefix:
        config.env_prefix.append("pvt_")
    if "zush_" not in config.env_prefix:
        config.env_prefix.append("zush_")
    if "pvt-" not in config.env_prefix:
        config.env_prefix.append("pvt-")
    if "zush-" not in config.env_prefix:
        config.env_prefix.append("zush-")
        
    config.envs.append(Path("C://Users\\zacka\\scoop\\apps\\python\\current\\Lib\\site-packages"))

    cli = create_ghzush_group(
        name="gh-for-zush",
        gh_config=gh_config,
        zush_config=config,
        execute_command=dry_run_execute_command if dry_run else None,
    )
    cli.main(args=click_argv, prog_name="gh-for-zush")


if __name__ == "__main__":
    main()
