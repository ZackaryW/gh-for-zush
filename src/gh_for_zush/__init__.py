"""Public package surface for gh-for-zush."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import TYPE_CHECKING
from collections.abc import Callable

from zush import create_zush_group
from zush.configparse.config import Config
from zush.core.storage import default_storage

from gh_for_zush.cache import InventoryCache
from gh_for_zush.cmd import create_system_commands
from gh_for_zush.utils import GhConfig

if TYPE_CHECKING:
	from zush.core.storage import ZushStorage


def create_ghzush_group(
	gh_config: GhConfig | None = None,
	*,
	name: str = "zush",
	zush_config: Config | None = None,
	storage: ZushStorage | None = None,
	mock_path: Path | None = None,
	execute_command: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
):
	"""Build a zush root group with gh-for-zush host commands injected into self."""
	resolved_gh_config = gh_config or GhConfig()
	resolved_storage = storage or default_storage()
	repository_prefixes = tuple(zush_config.env_prefix) if zush_config is not None else ()
	return create_zush_group(
		name=name,
		config=zush_config,
		storage=resolved_storage,
		mock_path=mock_path,
		system_commands=create_system_commands(
			resolved_gh_config,
			repository_prefixes=repository_prefixes,
			inventory_cache=InventoryCache(resolved_storage),
			execute_command=execute_command,
		),
	)


__all__ = ["GhConfig", "create_ghzush_group", "create_system_commands"]
