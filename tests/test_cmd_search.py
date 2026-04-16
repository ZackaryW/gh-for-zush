from click.testing import CliRunner

from gh_for_zush.cmd import create_system_commands
from gh_for_zush.utils import GhConfig
from zuu.v202602_1.gh import GitHubRepo


def test_sources_command_prints_default_owner_and_allowlist() -> None:
    runner = CliRunner()
    command = create_system_commands(
        GhConfig(default_owner="ZackaryW", allowed_owners=("ZackaryW", "Pathverse")),
    )["sources"]

    result = runner.invoke(command)

    assert result.exit_code == 0
    assert result.output == (
        "default_owner: ZackaryW\n"
        "allowed_owners:\n"
        "- ZackaryW\n"
        "- Pathverse\n"
    )


def test_sources_command_prints_effective_owner_from_presets() -> None:
    runner = CliRunner()
    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
    )["sources"]

    result = runner.invoke(command)

    assert result.exit_code == 0
    assert result.output == (
        "default_owner: ZackaryW\n"
        "allowed_owners:\n"
        "- ZackaryW\n"
        "- Pathverse\n"
    )


def test_sources_command_prints_none_when_no_boundary_is_configured() -> None:
    runner = CliRunner()
    command = create_system_commands()["sources"]

    result = runner.invoke(command)

    assert result.exit_code == 0
    assert result.output == (
        "default_owner: (none)\n"
        "allowed_owners: (none)\n"
    )


def test_search_command_uses_default_owner_and_prints_results() -> None:
    runner = CliRunner()
    observed: dict[str, str] = {}

    def search_repositories(query: str, owner: str) -> list[GitHubRepo]:
        observed["query"] = query
        observed["owner"] = owner
        return [
            GitHubRepo(
                name="gh-for-zush",
                description="GitHub-backed zush group wrapper",
                updated_at="2026-04-15T10:00:00Z",
            ),
        ]

    command = create_system_commands(
        GhConfig(default_owner="ZackaryW"),
        search_repositories=search_repositories,
    )["search"]

    result = runner.invoke(command, ["zush"])

    assert result.exit_code == 0
    assert observed == {"query": "zush", "owner": "ZackaryW"}
    assert "| owner" in result.output
    assert "| ZackaryW" in result.output
    assert "| gh-for-zush" in result.output
    assert "GitHub-backed zush group wrapper" in result.output


def test_search_command_filters_results_by_repository_prefixes() -> None:
    runner = CliRunner()

    def search_repositories(query: str, owner: str) -> list[GitHubRepo]:
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
        search_repositories=search_repositories,
        repository_prefixes=("zush",),
    )["search"]

    result = runner.invoke(command, ["z"])

    assert result.exit_code == 0
    assert "| zush" in result.output
    assert "portable-scoop" not in result.output


def test_search_command_uses_first_allowed_owner_when_wrapper_only_sets_presets() -> None:
    runner = CliRunner()
    observed: dict[str, str] = {}

    def search_repositories(query: str, owner: str) -> list[GitHubRepo]:
        observed["query"] = query
        observed["owner"] = owner
        return []

    command = create_system_commands(
        GhConfig(allowed_owners=("ZackaryW", "Pathverse")),
        search_repositories=search_repositories,
    )["search"]

    result = runner.invoke(command, ["zush"])

    assert result.exit_code == 0
    assert observed == {"query": "zush", "owner": "ZackaryW"}
    assert result.output == "(none)\n"


def test_search_command_accepts_explicit_owner_within_boundary() -> None:
    runner = CliRunner()
    observed: dict[str, str] = {}

    def search_repositories(query: str, owner: str) -> list[GitHubRepo]:
        observed["query"] = query
        observed["owner"] = owner
        return []

    command = create_system_commands(
        GhConfig(default_owner="ZackaryW", allowed_owners=("ZackaryW", "Pathverse")),
        search_repositories=search_repositories,
    )["search"]

    result = runner.invoke(command, ["zush", "--owner", "Pathverse"])

    assert result.exit_code == 0
    assert observed == {"query": "zush", "owner": "Pathverse"}
    assert result.output == "(none)\n"


def test_search_command_surfaces_boundary_errors_as_click_failures() -> None:
    runner = CliRunner()
    command = create_system_commands(
        GhConfig(allowed_owners=("Pathverse",)),
        search_repositories=lambda query, owner: [],
    )["search"]

    result = runner.invoke(command, ["zush", "--owner", "ZackaryW"])

    assert result.exit_code != 0
    assert "outside the configured boundary" in result.output


def test_search_command_explains_how_to_configure_default_owner() -> None:
    runner = CliRunner()
    command = create_system_commands(search_repositories=lambda query, owner: [])["search"]

    result = runner.invoke(command, ["zush"])

    assert result.exit_code != 0
    assert "--owner" in result.output
    assert "GhConfig(default_owner=...)" in result.output


def test_search_command_surfaces_provider_errors_as_click_failures() -> None:
    runner = CliRunner()
    command = create_system_commands(
        GhConfig(default_owner="ZackaryW"),
        search_repositories=lambda query, owner: (_ for _ in ()).throw(ValueError("bad gh output")),
    )["search"]

    result = runner.invoke(command, ["zush"])

    assert result.exit_code != 0
    assert "failed to search repositories for ZackaryW" in result.output