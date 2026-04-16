"""Package resolution lookup helpers for the gh-for-zush wrapper."""

from __future__ import annotations

from collections.abc import Callable


PackageConfirm = Callable[[str, set[str], tuple[str, ...]], bool]


def normalize_package_name(name: str) -> str:
    """Normalize one package or distribution name for resolution checks."""
    normalized = name.strip().lower()
    return normalized.replace("_", "-").replace(".", "-")


def builtin_method_names() -> tuple[str, ...]:
    """Return the supported built-in package resolution method names."""
    return ("distribution", "prefixless")


def is_package_resolved(
    package: str,
    installed_packages: set[str],
    repository_prefixes: tuple[str, ...] = (),
    *,
    method: str = "distribution",
    confirm_package: PackageConfirm | None = None,
) -> bool:
    """Return whether one package should be treated as resolved by the active lookup rule."""
    if confirm_package is not None:
        return confirm_package(package, installed_packages, repository_prefixes)
    if method == "distribution":
        return _confirm_distribution_match(package, installed_packages, repository_prefixes)
    if method == "prefixless":
        return _confirm_prefixless_match(package, installed_packages, repository_prefixes)
    supported_methods = ", ".join(builtin_method_names())
    raise ValueError(f"unknown pkgconfirm method '{method}'; supported methods: {supported_methods}")


def _confirm_distribution_match(
    package: str,
    installed_packages: set[str],
    repository_prefixes: tuple[str, ...],
) -> bool:
    """Confirm resolution by normalized distribution-name equality only."""
    del repository_prefixes
    normalized_package = normalize_package_name(package)
    return normalized_package in _normalize_installed_packages(installed_packages)


def _confirm_prefixless_match(
    package: str,
    installed_packages: set[str],
    repository_prefixes: tuple[str, ...],
) -> bool:
    """Confirm resolution by normalized distribution name or prefix-stripped fallback names."""
    normalized_installed_packages = _normalize_installed_packages(installed_packages)
    for candidate in _candidate_package_names(package, repository_prefixes):
        if candidate in normalized_installed_packages:
            return True
    return False


def _normalize_installed_packages(installed_packages: set[str]) -> set[str]:
    """Normalize one installed-package snapshot for lookup checks."""
    return {normalize_package_name(package) for package in installed_packages if package.strip()}


def _candidate_package_names(package: str, repository_prefixes: tuple[str, ...]) -> tuple[str, ...]:
    """Build the normalized package names that the built-in lookup methods may accept."""
    normalized_package = normalize_package_name(package)
    if not normalized_package:
        return ()
    candidates = [normalized_package]
    for prefix in repository_prefixes:
        normalized_prefix = prefix.strip().lower()
        if normalized_prefix and package.startswith(prefix):
            stripped_candidate = normalize_package_name(package[len(prefix):])
            if stripped_candidate and stripped_candidate not in candidates:
                candidates.append(stripped_candidate)
    return tuple(candidates)