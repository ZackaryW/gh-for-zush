from gh_for_zush.pkgconfirm import builtin_method_names, is_package_resolved, normalize_package_name


def test_normalize_package_name_collapses_common_distribution_separators() -> None:
    assert normalize_package_name(" zush_jobqueue.pkg ") == "zush-jobqueue-pkg"


def test_builtin_method_names_lists_supported_lookup_rules() -> None:
    assert builtin_method_names() == ("distribution", "prefixless")


def test_distribution_method_matches_normalized_distribution_name() -> None:
    assert is_package_resolved("zush_jobqueue", {"zush-jobqueue"}) is True


def test_distribution_method_rejects_unrelated_distribution_name() -> None:
    assert is_package_resolved("zush_jobqueue", {"jobqueue"}) is False


def test_prefixless_method_accepts_prefix_stripped_match() -> None:
    assert is_package_resolved(
        "zush_jobqueue",
        {"jobqueue"},
        repository_prefixes=("zush_", "zush-"),
        method="prefixless",
    ) is True


def test_prefixless_method_keeps_original_name_candidate() -> None:
    assert is_package_resolved(
        "zush_jobqueue",
        {"zush-jobqueue"},
        repository_prefixes=("zush_",),
        method="prefixless",
    ) is True


def test_custom_confirm_package_overrides_builtin_method() -> None:
    observed: dict[str, object] = {}

    def confirm_package(package: str, installed_packages: set[str], repository_prefixes: tuple[str, ...]) -> bool:
        observed["package"] = package
        observed["installed_packages"] = installed_packages
        observed["repository_prefixes"] = repository_prefixes
        return True

    assert is_package_resolved(
        "zush_jobqueue",
        {"anything"},
        repository_prefixes=("zush_",),
        confirm_package=confirm_package,
    ) is True
    assert observed == {
        "package": "zush_jobqueue",
        "installed_packages": {"anything"},
        "repository_prefixes": ("zush_",),
    }


def test_unknown_builtin_method_raises_value_error() -> None:
    try:
        is_package_resolved("zush_jobqueue", {"zush-jobqueue"}, method="made-up")
    except ValueError as exc:
        assert "unknown pkgconfirm method" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown pkgconfirm method")