from pathlib import Path

from gh_for_zush import GhConfig, create_ghzush_group
from zush.configparse.config import Config


def test_create_ghzush_group_accepts_explicit_zush_config_keyword(tmp_path: Path) -> None:
    cli = create_ghzush_group(
        gh_config=GhConfig(default_owner="ZackaryW"),
        zush_config=Config(envs=[], env_prefix=["zush_"], include_current_env=False),
        mock_path=tmp_path,
    )

    assert "self" in cli.commands
