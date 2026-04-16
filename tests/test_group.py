from pathlib import Path

import click

from gh_for_zush import GhConfig, create_ghzush_group
from zush.configparse.config import Config


def test_create_ghzush_group_adds_gh_commands_to_self_group(tmp_path: Path) -> None:
    cli = create_ghzush_group(
        gh_config=GhConfig(default_owner="ZackaryW"),
        zush_config=Config(envs=[], env_prefix=["zush_"], include_current_env=False),
        mock_path=tmp_path,
    )

    self_group = cli.commands["self"]
    assert isinstance(self_group, click.Group)

    assert "install" in self_group.commands
    assert "update" in self_group.commands
    assert "uninstall" in self_group.commands
    assert "status" in self_group.commands
    assert "sources" in self_group.commands
    assert "search" in self_group.commands
    assert "available" in self_group.commands
