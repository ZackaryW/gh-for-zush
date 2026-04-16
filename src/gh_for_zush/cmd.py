"""Click command builders for the gh-for-zush self command surface."""

from __future__ import annotations

from collections.abc import Callable
import importlib.metadata
import json
import subprocess

import click
from tabulate import tabulate
from zuu.v202602_1.gh import (
    GitHubRepo,
    parse_repository_search_output,
    run_command,
    search_repositories as _search_repositories,
)

from gh_for_zush.cache import CachedRepository, InventoryCache
from gh_for_zush.pkgconfirm import is_package_resolved, normalize_package_name
from gh_for_zush.utils import GhConfig


def create_system_commands(
    config: GhConfig | None = None,
    search_repositories: Callable[[str, str], list[GitHubRepo]] | None = None,
    list_repositories: Callable[[str], list[GitHubRepo]] | None = None,
    repository_prefixes: tuple[str, ...] = (),
    inventory_cache: InventoryCache | None = None,
    list_installed_packages: Callable[[], set[str]] | None = None,
    execute_command: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, click.Command]:
    """Build the host-owned zush self commands for GitHub-backed package actions."""
    resolved_config = config or GhConfig()
    resolved_search = search_repositories or _search_repositories
    resolved_list = list_repositories or _list_repositories
    resolved_inventory_cache = inventory_cache
    resolved_installed_packages = list_installed_packages or _list_installed_packages
    resolved_execute_command = execute_command or _execute_command
    return {
        "install": _build_install_command(
            resolved_config,
            inventory_cache,
            repository_prefixes,
            resolved_execute_command,
        ),
        "update": _build_update_command(
            resolved_config,
            inventory_cache,
            repository_prefixes,
            resolved_installed_packages,
            resolved_execute_command,
        ),
        "uninstall": _build_uninstall_command(
            inventory_cache,
            repository_prefixes,
            resolved_config,
            resolved_execute_command,
        ),
        "status": _build_status_command(resolved_inventory_cache, resolved_installed_packages),
        "sources": _build_sources_command(resolved_config),
        "search": _build_search_command(resolved_config, resolved_search, repository_prefixes),
        "available": _build_available_command(
            resolved_config,
            resolved_list,
            repository_prefixes,
            resolved_inventory_cache,
        ),
    }


def _build_install_command(
    config: GhConfig,
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
) -> click.Command:
    """Build the self install command bound to one GitHub command configuration."""
    return click.Command(
        "install",
        callback=_install_callback(config, inventory_cache, repository_prefixes, execute_command),
        params=[click.Argument(["repository"])],
        help="Install one GitHub-backed package from the wrapper inventory.",
    )


def _build_update_command(
    config: GhConfig,
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
    list_installed_packages: Callable[[], set[str]],
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
) -> click.Command:
    """Build the self update command bound to one GitHub command configuration."""
    return click.Command(
        "update",
        callback=_update_callback(
            config,
            inventory_cache,
            repository_prefixes,
            list_installed_packages,
            execute_command,
        ),
        params=[
            click.Argument(["repository"], required=False),
            click.Option(["-a", "--all"], is_flag=True, default=False),
        ],
        help="Update one GitHub-backed package or all installed cached packages.",
    )


def _build_uninstall_command(
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
    config: GhConfig,
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
) -> click.Command:
    """Build the self uninstall command bound to one GitHub command configuration."""
    return click.Command(
        "uninstall",
        callback=_uninstall_callback(config, inventory_cache, repository_prefixes, execute_command),
        params=[click.Argument(["package"])],
        help="Uninstall one installed package name.",
    )


def _build_status_command(
    inventory_cache: InventoryCache | None,
    list_installed_packages: Callable[[], set[str]],
) -> click.Command:
    """Build the self status command bound to cached inventory and install detection."""
    return click.Command(
        "status",
        callback=_status_callback(inventory_cache, list_installed_packages),
        help="Print cached package status for the wrapper inventory.",
    )


def _build_sources_command(config: GhConfig) -> click.Command:
    """Build the self sources command bound to one GitHub command configuration."""
    return click.Command(
        "sources",
        callback=_sources_callback(config),
        help="Print the configured default owner and owner boundary.",
    )


def _build_search_command(
    config: GhConfig,
    search_repositories: Callable[[str, str], list[GitHubRepo]],
    repository_prefixes: tuple[str, ...],
) -> click.Command:
    """Build the self search command bound to one GitHub query implementation."""
    return click.Command(
        "search",
        callback=_search_callback(config, search_repositories, repository_prefixes),
        params=[
            click.Argument(["query"]),
            click.Option(["--owner"], type=str, default=None),
        ],
        help="Search repositories within the configured owner boundary.",
    )


def _build_available_command(
    config: GhConfig,
    list_repositories: Callable[[str], list[GitHubRepo]],
    repository_prefixes: tuple[str, ...],
    inventory_cache: InventoryCache | None,
) -> click.Command:
    """Build the self available command bound to one GitHub repository listing implementation."""
    return click.Command(
        "available",
        callback=_available_callback(config, list_repositories, repository_prefixes, inventory_cache),
        params=[click.Option(["--refresh"], is_flag=True, default=False)],
        help="List all available repositories across the configured wrapper presets.",
    )


def _install_callback(
    config: GhConfig,
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
) -> Callable[[str], None]:
    """Build the install callback bound to one GitHub command configuration."""

    def callback(repository: str) -> None:
        """Install one repository after resolving cached shorthand names when possible."""
        resolved_repository = _resolve_cached_repository_name(repository, inventory_cache, repository_prefixes)
        _run_command_or_raise(execute_command, _render_or_raise(config.render_install_command, resolved_repository))

    return callback


def _update_callback(
    config: GhConfig,
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
    list_installed_packages: Callable[[], set[str]],
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
) -> Callable[[str | None, bool], None]:
    """Build the update callback bound to one GitHub command configuration."""

    def callback(repository: str | None, all: bool) -> None:
        """Update one repository or every installed cached repository when requested."""
        if all:
            _update_all_cached_repositories(config, inventory_cache, list_installed_packages, execute_command)
            return
        if repository is None:
            raise click.ClickException("update requires a repository or --all")
        resolved_repository = _resolve_cached_repository_name(repository, inventory_cache, repository_prefixes)
        _run_command_or_raise(execute_command, _render_or_raise(config.render_update_command, resolved_repository))

    return callback


def _uninstall_callback(
    config: GhConfig,
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
) -> Callable[[str], None]:
    """Build the uninstall callback bound to one GitHub command configuration."""

    def callback(package: str) -> None:
        """Uninstall one package after resolving cached shorthand names when possible."""
        resolved_package = _resolve_cached_package_name(package, inventory_cache, repository_prefixes)
        _run_command_or_raise(execute_command, _render_or_raise(config.render_remove_command, resolved_package))

    return callback


def _status_callback(
    inventory_cache: InventoryCache | None,
    list_installed_packages: Callable[[], set[str]],
) -> Callable[[], None]:
    """Build the status callback bound to cached inventory and install detection."""

    def callback() -> None:
        """Print cached repositories with installed-state information."""
        cached_repositories = inventory_cache.load_available() if inventory_cache is not None else []
        if not cached_repositories:
            click.echo("No cached inventory. Run 'self available' first.")
            return
        installed_packages = list_installed_packages()
        click.echo(_render_cached_status_table(cached_repositories, installed_packages))

    return callback


def _sources_callback(config: GhConfig) -> Callable[[], None]:
    """Build the sources callback bound to one GitHub command configuration."""

    def callback() -> None:
        """Print the current default owner and configured owner boundary."""
        default_owner = config.resolve_search_owner(None) or "(none)"
        click.echo(f"default_owner: {default_owner}")
        if not config.allowed_owners:
            click.echo("allowed_owners: (none)")
            return
        click.echo("allowed_owners:")
        for owner in config.allowed_owners:
            click.echo(f"- {owner}")

    return callback


def _search_callback(
    config: GhConfig,
    search_repositories: Callable[[str, str], list[GitHubRepo]],
    repository_prefixes: tuple[str, ...],
) -> Callable[[str, str | None], None]:
    """Build the search callback bound to one GitHub command configuration."""

    def callback(query: str, owner: str | None) -> None:
        """Search repositories for one query within the configured boundary and print matches."""
        resolved_owner = _resolve_search_owner_or_raise(config, owner)
        results = _filter_repositories_by_prefix(
            _search_repositories_or_raise(search_repositories, query, resolved_owner),
            repository_prefixes,
        )
        if not results:
            click.echo("(none)")
            return
        click.echo(_render_repository_table([(resolved_owner, repository) for repository in results]))

    return callback


def _available_callback(
    config: GhConfig,
    list_repositories: Callable[[str], list[GitHubRepo]],
    repository_prefixes: tuple[str, ...],
    inventory_cache: InventoryCache | None,
) -> Callable[[bool], None]:
    """Build the available callback bound to one GitHub command configuration."""

    def callback(refresh: bool) -> None:
        """List available repositories across the configured wrapper presets and print them as a table."""
        if not refresh and inventory_cache is not None:
            cached_rows = inventory_cache.load_available()
            if cached_rows:
                click.echo(_render_cached_available_table(cached_rows))
                return
        owners = _resolve_available_owners_or_raise(config)
        rows: list[tuple[str, GitHubRepo]] = []
        for owner in owners:
            rows.extend(
                (owner, repository)
                for repository in _filter_repositories_by_prefix(
                    _list_repositories_or_raise(list_repositories, owner),
                    repository_prefixes,
                )
            )
        if not rows:
            if inventory_cache is not None:
                inventory_cache.save_available([])
            click.echo("(none)")
            return
        if inventory_cache is not None:
            inventory_cache.save_available(rows)
        click.echo(_render_repository_table(rows))

    return callback


def _render_or_raise(renderer: Callable[[str], str], value: str) -> str:
    """Render one command value and translate config validation failures into Click errors."""
    try:
        return renderer(value)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _run_command_or_raise(
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
    command: str,
) -> None:
    """Run one rendered shell command and surface failures as Click errors."""
    try:
        result = execute_command(command)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(f"failed to execute command: {exc}") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip() or f"command failed: {command}"
        raise click.ClickException(message)
    if result.stdout:
        click.echo(result.stdout, nl=False)


def _update_all_cached_repositories(
    config: GhConfig,
    inventory_cache: InventoryCache | None,
    list_installed_packages: Callable[[], set[str]],
    execute_command: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    """Update every cached repository whose normalized package name is currently installed."""
    cached_repositories = inventory_cache.load_available() if inventory_cache is not None else []
    if not cached_repositories:
        raise click.ClickException("No cached inventory. Run 'self available' first.")
    installed_packages = list_installed_packages()
    matching_repositories = [
        repository
        for repository in cached_repositories
        if is_package_resolved(repository.name, installed_packages)
    ]
    if not matching_repositories:
        click.echo("No installed cached packages to update.")
        return
    for repository in matching_repositories:
        command = _render_or_raise(config.render_update_command, f"{repository.owner}/{repository.name}")
        _run_command_or_raise(execute_command, command)


def _execute_command(command: str) -> subprocess.CompletedProcess[str]:
    """Execute one rendered shell command through the host shell and capture output."""
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve_search_owner_or_raise(config: GhConfig, owner: str | None) -> str:
    """Resolve one search owner and translate missing or invalid owners into Click errors."""
    try:
        resolved_owner = config.resolve_search_owner(owner)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if resolved_owner is None:
        raise click.ClickException(
            "search requires --owner when no default_owner is configured; "
            "pass --owner or construct GhConfig(default_owner=...)"
        )
    return resolved_owner


def _resolve_available_owners_or_raise(config: GhConfig) -> list[str]:
    """Resolve the owner presets used by the available command or raise when none exist."""
    if config.allowed_owners:
        return list(config.allowed_owners)
    resolved_owner = config.resolve_search_owner(None)
    if resolved_owner is None:
        raise click.ClickException("available requires a preset owner boundary or default owner")
    return [resolved_owner]


def _render_repository_table(rows: list[tuple[str, GitHubRepo]]) -> str:
    """Render one repository result set as a tabulated owner/name/update/description table."""
    table_rows = [
        (owner, repository.name, repository.updated_at, repository.description or "")
        for owner, repository in rows
    ]
    return tabulate(
        table_rows,
        headers=("owner", "name", "updated_at", "description"),
        tablefmt="github",
    )


def _render_cached_available_table(repositories: list[CachedRepository]) -> str:
    """Render cached available repositories as the same table shape as live inventory."""
    table_rows = [
        (repository.owner, repository.name, repository.updated_at, repository.description)
        for repository in repositories
    ]
    return tabulate(
        table_rows,
        headers=("owner", "name", "updated_at", "description"),
        tablefmt="github",
    )


def _render_cached_status_table(
    repositories: list[CachedRepository],
    installed_packages: set[str],
) -> str:
    """Render cached repositories with installed-state information as a table."""
    table_rows = [
        (
            repository.owner,
            repository.name,
            "yes" if is_package_resolved(repository.name, installed_packages) else "no",
            repository.updated_at,
            repository.description,
        )
        for repository in repositories
    ]
    return tabulate(
        table_rows,
        headers=("owner", "name", "installed", "updated_at", "description"),
        tablefmt="github",
    )


def _filter_repositories_by_prefix(
    repositories: list[GitHubRepo],
    repository_prefixes: tuple[str, ...],
) -> list[GitHubRepo]:
    """Filter repositories by configured name prefixes when wrapper presets provide them."""
    normalized_prefixes = tuple(prefix for prefix in repository_prefixes if prefix)
    if not normalized_prefixes:
        return repositories
    return [
        repository
        for repository in repositories
        if repository.name.startswith(normalized_prefixes)
    ]


def _resolve_cached_repository_name(
    repository: str,
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
) -> str:
    """Resolve one repository input through cached lossy prefix matching when possible."""
    candidate = repository.strip()
    if not candidate or "/" in candidate or inventory_cache is None:
        return repository
    cached_repositories = inventory_cache.load_available()
    if not cached_repositories:
        return repository
    matches = _find_lossy_cached_matches(candidate, cached_repositories, repository_prefixes)
    if not matches:
        return repository
    if len(matches) > 1:
        match_list = ", ".join(f"{match.owner}/{match.name}" for match in matches)
        raise click.ClickException(f"ambiguous cached repository match for '{candidate}': {match_list}")
    match = matches[0]
    return f"{match.owner}/{match.name}"


def _resolve_cached_package_name(
    package: str,
    inventory_cache: InventoryCache | None,
    repository_prefixes: tuple[str, ...],
) -> str:
    """Resolve one package input through cached lossy prefix matching when possible."""
    candidate = package.strip()
    if not candidate or inventory_cache is None:
        return package
    cached_repositories = inventory_cache.load_available()
    if not cached_repositories:
        return package
    matches = _find_lossy_cached_matches(candidate, cached_repositories, repository_prefixes)
    if not matches:
        return package
    if len(matches) > 1:
        match_list = ", ".join(f"{match.owner}/{match.name}" for match in matches)
        raise click.ClickException(f"ambiguous cached repository match for '{candidate}': {match_list}")
    return matches[0].name


def _find_lossy_cached_matches(
    candidate: str,
    repositories: list[CachedRepository],
    repository_prefixes: tuple[str, ...],
) -> list[CachedRepository]:
    """Find cached repositories whose names match one short user token after preset prefix stripping."""
    normalized_candidate = candidate.strip()
    if not normalized_candidate:
        return []
    normalized_prefixes = tuple(prefix for prefix in repository_prefixes if prefix)
    matches: list[CachedRepository] = []
    for repository in repositories:
        if repository.name == normalized_candidate:
            matches.append(repository)
            continue
        for prefix in normalized_prefixes:
            if repository.name.startswith(prefix) and repository.name[len(prefix):] == normalized_candidate:
                matches.append(repository)
                break
    return matches


def _search_repositories_or_raise(
    search_repositories: Callable[[str, str], list[GitHubRepo]],
    query: str,
    owner: str,
) -> list[GitHubRepo]:
    """Run one repository search provider and translate provider failures into Click errors."""
    try:
        return search_repositories(query, owner)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(f"failed to search repositories for {owner}: {exc}") from exc


def _list_repositories_or_raise(
    list_repositories: Callable[[str], list[GitHubRepo]],
    owner: str,
) -> list[GitHubRepo]:
    """Run one repository listing provider and translate provider failures into Click errors."""
    try:
        return list_repositories(owner)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(f"failed to list repositories for {owner}: {exc}") from exc


def _list_repositories(owner: str) -> list[GitHubRepo]:
    """List repositories for one owner through the GitHub CLI."""
    result = run_command(
        "gh",
        ["repo", "list", owner, "--limit", "1000", "--json", "updatedAt,description,name"],
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip() or "unknown gh error"
        raise click.ClickException(f"failed to list repositories for {owner}: {message}")
    payload = result.stdout.strip()
    if not payload:
        return []
    try:
        return parse_repository_search_output(payload)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"failed to list repositories for {owner}: invalid gh JSON output") from exc


def _list_installed_packages() -> set[str]:
    """List normalized installed distribution names for status checks."""
    installed_packages: set[str] = set()
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if not name:
            continue
        installed_packages.add(normalize_package_name(name))
    return installed_packages