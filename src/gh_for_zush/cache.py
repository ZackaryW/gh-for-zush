"""Persistent cache utilities for the gh-for-zush wrapper surface."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING

from zuu.v202602_1.gh import GitHubRepo

if TYPE_CHECKING:
    from zush.core.storage import ZushStorage


@dataclass(frozen=True)
class CachedRepository:
    """One cached repository row used by available and status views."""

    owner: str
    name: str
    description: str
    updated_at: str


class InventoryCache:
    """Persist and reload the preset-scoped available inventory for wrapper status views."""

    def __init__(self, storage: ZushStorage) -> None:
        """Bind the cache helper to one zush storage target."""
        self._storage = storage

    def load_available(self) -> list[CachedRepository]:
        """Load the cached available inventory from disk when it exists."""
        cache_path = self._cache_path()
        if not cache_path.exists():
            return []
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        repositories = payload.get("available", []) if isinstance(payload, dict) else []
        if not isinstance(repositories, list):
            return []
        loaded: list[CachedRepository] = []
        for repository in repositories:
            if not isinstance(repository, dict):
                continue
            try:
                loaded.append(CachedRepository(**repository))
            except TypeError:
                continue
        return loaded

    def save_available(self, repositories: list[tuple[str, GitHubRepo]]) -> list[CachedRepository]:
        """Persist one available inventory snapshot to disk and return the saved rows."""
        cached_repositories = [
            CachedRepository(
                owner=owner,
                name=repository.name,
                description=repository.description or "",
                updated_at=repository.updated_at,
            )
            for owner, repository in repositories
        ]
        cache_path = self._cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"available": [asdict(repository) for repository in cached_repositories]}
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return cached_repositories

    def _cache_path(self) -> Path:
        """Return the cache file used by the wrapper inventory surface."""
        return self._storage.config_dir() / "gh-for-zush-cache.json"