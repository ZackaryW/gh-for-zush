import subprocess

from click.testing import CliRunner
from zush.core.storage import DirectoryStorage

from gh_for_zush.cache import InventoryCache
from gh_for_zush.cmd import create_system_commands
from gh_for_zush.utils import GhConfig
from zuu.v202602_1.gh import GitHubRepo


def test_create_system_commands_returns_all_expected_commands() -> None:
    commands = create_system_commands()

    assert tuple(commands) == (
        "install",
        "update",
        "uninstall",
        "status",
        "sources",
        "search",
        "available",
    )


def test_install_command_executes_repository_command() -> None:
    runner = CliRunner()
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="installed\n", stderr="")

    command = create_system_commands(
        GhConfig(default_owner="ZackaryW"),
        execute_command=execute_command,
    )["install"]

    result = runner.invoke(command, ["gh-for-zush"])

    assert result.exit_code == 0
    assert executed == ["pip install git+https://github.com/ZackaryW/gh-for-zush.git"]
    assert result.output == "installed\n"


def test_install_command_uses_first_allowed_owner_when_wrapper_only_sets_presets() -> None:
    runner = CliRunner()
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        execute_command=execute_command,
    )["install"]

    result = runner.invoke(command, ["zush_jobqueue"])

    assert result.exit_code == 0
    assert executed == ["pip install git+https://github.com/ZackaryW/zush_jobqueue.git"]


def test_install_command_uses_lossy_cached_match_when_prefixes_make_one_result(tmp_path) -> None:
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
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        repository_prefixes=("zush_", "zush-", "pvt_", "pvt-"),
        inventory_cache=inventory_cache,
        execute_command=execute_command,
    )["install"]

    result = runner.invoke(command, ["jobqueue"])

    assert result.exit_code == 0
    assert executed == ["pip install git+https://github.com/ZackaryW/zush_jobqueue.git"]


def test_install_command_rejects_ambiguous_lossy_cached_match(tmp_path) -> None:
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
            (
                "Pathverse",
                GitHubRepo(
                    name="pvt_jobqueue",
                    description="pathverse job queue",
                    updated_at="2026-04-16T08:00:00Z",
                ),
            ),
        ]
    )
    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        repository_prefixes=("zush_", "pvt_"),
        inventory_cache=inventory_cache,
        execute_command=lambda command: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
    )["install"]

    result = runner.invoke(command, ["jobqueue"])

    assert result.exit_code != 0
    assert "ambiguous" in result.output


def test_install_command_surfaces_config_errors_as_click_failures() -> None:
    runner = CliRunner()
    command = create_system_commands(
        execute_command=lambda command: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
    )["install"]

    result = runner.invoke(command, ["gh-for-zush"])

    assert result.exit_code != 0
    assert "owner/name" in result.output


def test_update_command_executes_repository_command() -> None:
    runner = CliRunner()
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="updated\n", stderr="")

    command = create_system_commands(execute_command=execute_command)["update"]

    result = runner.invoke(command, ["Pathverse/gh-for-zush"])

    assert result.exit_code == 0
    assert executed == ["pip install -U git+https://github.com/Pathverse/gh-for-zush.git"]
    assert result.output == "updated\n"


def test_update_command_uses_lossy_cached_match_when_prefixes_make_one_result(tmp_path) -> None:
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
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        repository_prefixes=("zush_", "zush-", "pvt_", "pvt-"),
        inventory_cache=inventory_cache,
        execute_command=execute_command,
    )["update"]

    result = runner.invoke(command, ["jobqueue"])

    assert result.exit_code == 0
    assert executed == ["pip install -U git+https://github.com/ZackaryW/zush_jobqueue.git"]


def test_update_command_supports_all_for_installed_cached_packages(tmp_path) -> None:
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
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        inventory_cache=inventory_cache,
        list_installed_packages=lambda: {"zush-jobqueue"},
        execute_command=execute_command,
    )["update"]

    result = runner.invoke(command, ["--all"])

    assert result.exit_code == 0
    assert executed == ["pip install -U git+https://github.com/ZackaryW/zush_jobqueue.git"]


def test_update_command_all_requires_cached_inventory(tmp_path) -> None:
    runner = CliRunner()
    command = create_system_commands(
        inventory_cache=InventoryCache(DirectoryStorage(tmp_path)),
        execute_command=lambda command: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
    )["update"]

    result = runner.invoke(command, ["--all"])

    assert result.exit_code != 0
    assert "No cached inventory" in result.output


def test_uninstall_command_executes_package_command() -> None:
    runner = CliRunner()
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="removed\n", stderr="")

    command = create_system_commands(execute_command=execute_command)["uninstall"]

    result = runner.invoke(command, [" gh-for-zush "])

    assert result.exit_code == 0
    assert executed == ["pip uninstall gh-for-zush"]
    assert result.output == "removed\n"


def test_uninstall_command_uses_lossy_cached_match_when_prefixes_make_one_result(tmp_path) -> None:
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
    executed: list[str] = []

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        repository_prefixes=("zush_", "zush-", "pvt_", "pvt-"),
        inventory_cache=inventory_cache,
        execute_command=execute_command,
    )["uninstall"]

    result = runner.invoke(command, ["jobqueue"])

    assert result.exit_code == 0
    assert executed == ["pip uninstall zush_jobqueue"]


def test_action_command_surfaces_executor_failures_as_click_failures() -> None:
    runner = CliRunner()

    def execute_command(command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    command = create_system_commands(
        GhConfig(default_owner="ZackaryW"),
        execute_command=execute_command,
    )["install"]

    result = runner.invoke(command, ["gh-for-zush"])

    assert result.exit_code != 0
    assert "boom" in result.output