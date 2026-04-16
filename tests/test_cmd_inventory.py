from click.testing import CliRunner
from zush.core.storage import DirectoryStorage

from gh_for_zush.cache import InventoryCache
from gh_for_zush.cmd import create_system_commands
from gh_for_zush.utils import GhConfig
from zuu.v202602_1.gh import GitHubRepo


def test_status_command_prints_cached_inventory_with_install_state(tmp_path) -> None:
    runner = CliRunner()
    inventory_cache = InventoryCache(DirectoryStorage(tmp_path))
    inventory_cache.save_available(
        [
            (
                "ZackaryW",
                GitHubRepo(
                    name="zush",
                    description="zack's useful shell",
                    updated_at="2026-04-16T05:31:30Z",
                ),
            ),
            (
                "Pathverse",
                GitHubRepo(
                    name="pvt_clone",
                    description="pvt extension for repo syncing",
                    updated_at="2026-03-27T05:46:53Z",
                ),
            ),
        ]
    )
    command = create_system_commands(
        inventory_cache=inventory_cache,
        list_installed_packages=lambda: {"zush"},
    )["status"]

    result = runner.invoke(command)

    assert result.exit_code == 0
    assert "| owner" in result.output
    assert "| installed" in result.output
    assert "| ZackaryW" in result.output
    assert "| zush" in result.output
    assert "| yes" in result.output
    assert "| pvt_clone" in result.output
    assert "| no" in result.output


def test_status_command_guides_user_when_cache_is_empty(tmp_path) -> None:
    runner = CliRunner()
    command = create_system_commands(
        inventory_cache=InventoryCache(DirectoryStorage(tmp_path)),
    )["status"]

    result = runner.invoke(command)

    assert result.exit_code == 0
    assert result.output == "No cached inventory. Run 'self available' first.\n"


def test_available_command_lists_all_packages_across_allowed_owners() -> None:
    runner = CliRunner()
    observed: list[str] = []

    def list_repositories(owner: str) -> list[GitHubRepo]:
        observed.append(owner)
        if owner == "ZackaryW":
            return [
                GitHubRepo(
                    name="zush",
                    description="zack's useful shell",
                    updated_at="2026-04-16T05:31:30Z",
                ),
            ]
        return [
            GitHubRepo(
                name="portable-scoop",
                description="running a limited scoop on usb drive",
                updated_at="2025-10-19T18:52:46Z",
            ),
        ]

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        list_repositories=list_repositories,
    )["available"]

    result = runner.invoke(command, ["--refresh"])

    assert result.exit_code == 0
    assert observed == ["ZackaryW", "Pathverse"]
    assert "| owner" in result.output
    assert "| ZackaryW" in result.output
    assert "| Pathverse" in result.output
    assert "| zush" in result.output
    assert "| portable-scoop" in result.output


def test_available_command_uses_cached_inventory_without_refresh(tmp_path) -> None:
    runner = CliRunner()
    inventory_cache = InventoryCache(DirectoryStorage(tmp_path))
    inventory_cache.save_available(
        [
            (
                "ZackaryW",
                GitHubRepo(
                    name="zush_jobqueue",
                    description="zush extension for script execution jobs",
                    updated_at="2026-03-22T20:37:16Z",
                ),
            ),
        ]
    )

    def list_repositories(owner: str) -> list[GitHubRepo]:
        raise AssertionError("live listing should not run when cache exists")

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW",)),
        list_repositories=list_repositories,
        inventory_cache=inventory_cache,
    )["available"]

    result = runner.invoke(command)

    assert result.exit_code == 0
    assert "| zush_jobqueue" in result.output


def test_available_command_refreshes_cache_when_requested(tmp_path) -> None:
    runner = CliRunner()
    inventory_cache = InventoryCache(DirectoryStorage(tmp_path))
    inventory_cache.save_available(
        [
            (
                "ZackaryW",
                GitHubRepo(
                    name="zush_jobqueue",
                    description="old entry",
                    updated_at="2026-03-22T20:37:16Z",
                ),
            ),
        ]
    )

    def list_repositories(owner: str) -> list[GitHubRepo]:
        return [
            GitHubRepo(
                name="zush_ylock",
                description="refreshed entry",
                updated_at="2026-04-05T00:10:14Z",
            ),
        ]

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW",)),
        list_repositories=list_repositories,
        inventory_cache=inventory_cache,
    )["available"]

    result = runner.invoke(command, ["--refresh"])

    assert result.exit_code == 0
    assert "| zush_ylock" in result.output
    assert "zush_jobqueue" not in result.output


def test_available_command_writes_cached_inventory(tmp_path) -> None:
    runner = CliRunner()
    inventory_cache = InventoryCache(DirectoryStorage(tmp_path))

    def list_repositories(owner: str) -> list[GitHubRepo]:
        return [
            GitHubRepo(
                name="zush",
                description="zack's useful shell",
                updated_at="2026-04-16T05:31:30Z",
            ),
        ]

    command = create_system_commands(
        GhConfig(default_owner="ZackaryW"),
        list_repositories=list_repositories,
        inventory_cache=inventory_cache,
    )["available"]

    result = runner.invoke(command, ["--refresh"])

    assert result.exit_code == 0
    cached_repositories = inventory_cache.load_available()
    assert [repository.owner for repository in cached_repositories] == ["ZackaryW"]
    assert [repository.name for repository in cached_repositories] == ["zush"]


def test_available_command_filters_results_by_repository_prefixes() -> None:
    runner = CliRunner()

    def list_repositories(owner: str) -> list[GitHubRepo]:
        return [
            GitHubRepo(
                name="zush",
                description="zack's useful shell",
                updated_at="2026-04-16T05:31:30Z",
            ),
            GitHubRepo(
                name="portable-scoop",
                description="running a limited scoop on usb drive",
                updated_at="2025-10-19T18:52:46Z",
            ),
        ]

    command = create_system_commands(
        GhConfig(default_owner="ZackaryW"),
        list_repositories=list_repositories,
        repository_prefixes=("zush",),
    )["available"]

    result = runner.invoke(command, ["--refresh"])

    assert result.exit_code == 0
    assert "| zush" in result.output
    assert "portable-scoop" not in result.output


def test_available_command_uses_effective_owner_when_only_one_preset_exists() -> None:
    runner = CliRunner()
    observed: list[str] = []

    def list_repositories(owner: str) -> list[GitHubRepo]:
        observed.append(owner)
        return []

    command = create_system_commands(
        GhConfig(default_owner="ZackaryW"),
        list_repositories=list_repositories,
    )["available"]

    result = runner.invoke(command, ["--refresh"])

    assert result.exit_code == 0
    assert observed == ["ZackaryW"]
    assert result.output == "(none)\n"


def test_available_command_requires_presets_when_no_owner_can_be_resolved() -> None:
    runner = CliRunner()
    command = create_system_commands(list_repositories=lambda owner: [])["available"]

    result = runner.invoke(command, ["--refresh"])

    assert result.exit_code != 0
    assert "available requires a preset owner boundary" in result.output


def test_available_command_surfaces_listing_errors_as_click_failures() -> None:
    runner = CliRunner()
    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW",)),
        list_repositories=lambda owner: (_ for _ in ()).throw(ValueError("bad gh output")),
    )["available"]

    result = runner.invoke(command, ["--refresh"])

    assert result.exit_code != 0
    assert "failed to list repositories for ZackaryW" in result.output