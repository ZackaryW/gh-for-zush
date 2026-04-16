import pytest

from gh_for_zush.utils import GhConfig


def test_gh_config_normalizes_boundary_and_commands() -> None:
    config = GhConfig(
        default_owner=" ZackaryW ",
        allowed_owners=(" ZackaryW ", "Pathverse", "Pathverse "),
        install_cmd=" pip install git+{url} ",
        update_cmd=" pip install -U git+{url} ",
        remove_cmd=" pip uninstall {package} ",
    )

    assert config.default_owner == "ZackaryW"
    assert config.allowed_owners == ("ZackaryW", "Pathverse")
    assert config.install_cmd == "pip install git+{url}"
    assert config.update_cmd == "pip install -U git+{url}"
    assert config.remove_cmd == "pip uninstall {package}"


def test_gh_config_uses_pip_commands_by_default() -> None:
    config = GhConfig()

    assert config.install_cmd == "pip install git+{url}"
    assert config.update_cmd == "pip install -U git+{url}"
    assert config.remove_cmd == "pip uninstall {package}"


def test_gh_config_rejects_default_owner_outside_allowed_owners() -> None:
    with pytest.raises(ValueError, match="default_owner"):
        GhConfig(
            default_owner="ZackaryW",
            allowed_owners=("Pathverse",),
        )


def test_gh_config_rejects_blank_command_values() -> None:
    with pytest.raises(ValueError, match="install_cmd"):
        GhConfig(install_cmd="   ")


def test_gh_config_rejects_install_command_without_url_placeholder() -> None:
    with pytest.raises(ValueError, match="install_cmd"):
        GhConfig(install_cmd="pip install gh-for-zush")


def test_gh_config_rejects_update_command_without_url_placeholder() -> None:
    with pytest.raises(ValueError, match="update_cmd"):
        GhConfig(update_cmd="pip install -U gh-for-zush")


def test_gh_config_rejects_remove_command_without_package_placeholder() -> None:
    with pytest.raises(ValueError, match="remove_cmd"):
        GhConfig(remove_cmd="pip uninstall gh-for-zush")


def test_gh_config_resolves_short_repository_with_default_owner() -> None:
    config = GhConfig(default_owner="ZackaryW")

    assert config.resolve_repository("gh-for-zush") == "ZackaryW/gh-for-zush"


def test_gh_config_resolves_short_repository_with_first_allowed_owner() -> None:
    config = GhConfig(allowed_owners=("ZackaryW", "Pathverse"))

    assert config.resolve_repository("zush_jobqueue") == "ZackaryW/zush_jobqueue"


def test_gh_config_rejects_repository_owner_outside_boundary() -> None:
    config = GhConfig(allowed_owners=("Pathverse",))

    with pytest.raises(ValueError, match="outside the configured boundary"):
        config.resolve_repository("ZackaryW/gh-for-zush")


def test_gh_config_uses_default_owner_for_unscoped_search() -> None:
    config = GhConfig(default_owner="ZackaryW")

    assert config.resolve_search_owner(None) == "ZackaryW"


def test_gh_config_uses_first_allowed_owner_for_unscoped_search_without_default() -> None:
    config = GhConfig(allowed_owners=("ZackaryW", "Pathverse"))

    assert config.resolve_search_owner(None) == "ZackaryW"


def test_gh_config_normalizes_and_accepts_explicit_search_owner() -> None:
    config = GhConfig(allowed_owners=("ZackaryW",))

    assert config.resolve_search_owner(" ZackaryW ") == "ZackaryW"


def test_gh_config_renders_install_command_with_resolved_repository() -> None:
    config = GhConfig(
        default_owner="ZackaryW",
        install_cmd="pip install git+{url}",
    )

    assert config.render_install_command("gh-for-zush") == "pip install git+https://github.com/ZackaryW/gh-for-zush.git"


def test_gh_config_renders_update_command_with_explicit_repository() -> None:
    config = GhConfig(
        update_cmd="pip install -U git+{url}",
    )

    assert config.render_update_command("Pathverse/gh-for-zush") == "pip install -U git+https://github.com/Pathverse/gh-for-zush.git"


def test_gh_config_renders_remove_command_with_trimmed_package_name() -> None:
    config = GhConfig(remove_cmd="pip uninstall {package}")

    assert config.render_remove_command(" gh-for-zush ") == "pip uninstall gh-for-zush"


def test_gh_config_rejects_render_when_command_template_is_missing() -> None:
    config = GhConfig(install_cmd=None)

    with pytest.raises(ValueError, match="install_cmd"):
        config.render_install_command("gh-for-zush")