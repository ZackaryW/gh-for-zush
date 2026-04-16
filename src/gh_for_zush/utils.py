"""Small utility types for the gh-for-zush rebuild."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GhConfig:
    """Normalize the small configuration values needed by early features."""

    default_owner: str | None = None
    allowed_owners: tuple[str, ...] = ()
    install_cmd: str | None = "pip install git+{url}"
    update_cmd: str | None = "pip install -U git+{url}"
    remove_cmd: str | None = "pip uninstall {package} -y"

    def __post_init__(self) -> None:
        """Normalize owner fields and command template input into stable values."""
        normalized_default_owner = self._normalize_optional_owner(self.default_owner)
        normalized_allowed_owners = self._normalize_allowed_owners(self.allowed_owners)
        normalized_install_cmd = self._normalize_optional_command("install_cmd", self.install_cmd)
        normalized_update_cmd = self._normalize_optional_command("update_cmd", self.update_cmd)
        normalized_remove_cmd = self._normalize_optional_command("remove_cmd", self.remove_cmd)
        self._assert_required_placeholder("install_cmd", normalized_install_cmd, "{url}")
        self._assert_required_placeholder("update_cmd", normalized_update_cmd, "{url}")
        self._assert_required_placeholder("remove_cmd", normalized_remove_cmd, "{package}")
        if normalized_default_owner is not None and normalized_allowed_owners and normalized_default_owner not in normalized_allowed_owners:
            raise ValueError("default_owner must be included in allowed_owners")
        object.__setattr__(self, "default_owner", normalized_default_owner)
        object.__setattr__(self, "allowed_owners", normalized_allowed_owners)
        object.__setattr__(self, "install_cmd", normalized_install_cmd)
        object.__setattr__(self, "update_cmd", normalized_update_cmd)
        object.__setattr__(self, "remove_cmd", normalized_remove_cmd)

    def resolve_repository(self, repository: str) -> str:
        """Resolve one repository input into a stable owner/name reference."""
        candidate = repository.strip()
        if not candidate:
            raise ValueError("repository must not be empty")
        if "/" not in candidate:
            resolved_owner = self.resolve_search_owner(None)
            if resolved_owner is None:
                raise ValueError("repository must use 'owner/name' when no default_owner is configured")
            self._assert_owner_allowed(resolved_owner)
            return f"{resolved_owner}/{candidate}"
        owner, name = candidate.split("/", 1)
        normalized_owner = self._normalize_optional_owner(owner)
        normalized_name = name.strip()
        if normalized_owner is None or not normalized_name:
            raise ValueError("repository must use 'owner/name'")
        self._assert_owner_allowed(normalized_owner)
        return f"{normalized_owner}/{normalized_name}"

    def resolve_search_owner(self, owner: str | None) -> str | None:
        """Resolve one optional search owner within the configured boundary."""
        normalized_owner = self._normalize_optional_owner(owner)
        if normalized_owner is not None:
            self._assert_owner_allowed(normalized_owner)
            return normalized_owner
        if self.default_owner is not None:
            self._assert_owner_allowed(self.default_owner)
            return self.default_owner
        if self.allowed_owners:
            return self.allowed_owners[0]
        return None

    def render_install_command(self, repository: str) -> str:
        """Render one install command by injecting the resolved repository."""
        template = self._require_command_template("install_cmd", self.install_cmd)
        return template.format(url=self._build_repository_url(repository))

    def render_update_command(self, repository: str) -> str:
        """Render one update command by injecting the resolved repository."""
        template = self._require_command_template("update_cmd", self.update_cmd)
        return template.format(url=self._build_repository_url(repository))

    def render_remove_command(self, package: str) -> str:
        """Render one remove command by injecting the normalized package name."""
        template = self._require_command_template("remove_cmd", self.remove_cmd)
        return template.format(package=self._normalize_package_name(package))

    def _normalize_optional_owner(self, owner: str | None) -> str | None:
        """Strip one optional owner value and collapse empty strings to None."""
        if owner is None:
            return None
        candidate = owner.strip()
        return candidate or None

    def _normalize_allowed_owners(self, owners: tuple[str, ...]) -> tuple[str, ...]:
        """Strip, deduplicate, and preserve order for allowed owner names."""
        normalized_owners: list[str] = []
        for owner in owners:
            candidate = owner.strip()
            if not candidate or candidate in normalized_owners:
                continue
            normalized_owners.append(candidate)
        return tuple(normalized_owners)

    def _normalize_optional_command(self, field_name: str, command: str | None) -> str | None:
        """Strip one optional command template and reject blank values."""
        if command is None:
            return None
        normalized_command = command.strip()
        if not normalized_command:
            raise ValueError(f"{field_name} must not be blank")
        return normalized_command

    def _assert_required_placeholder(self, field_name: str, command: str | None, placeholder: str) -> None:
        """Require one placeholder token when a command template is configured."""
        if command is None:
            return
        if placeholder not in command:
            raise ValueError(f"{field_name} must include {placeholder}")

    def _require_command_template(self, field_name: str, command: str | None) -> str:
        """Return one configured command template or raise when it is missing."""
        if command is None:
            raise ValueError(f"{field_name} is not configured")
        return command

    def _normalize_package_name(self, package: str) -> str:
        """Strip one package name and reject blank values."""
        normalized_package = package.strip()
        if not normalized_package:
            raise ValueError("package must not be empty")
        return normalized_package

    def _build_repository_url(self, repository: str) -> str:
        """Build one canonical GitHub repository URL from a repository reference."""
        resolved_repository = self.resolve_repository(repository)
        return f"https://github.com/{resolved_repository}.git"

    def _assert_owner_allowed(self, owner: str) -> None:
        """Raise when one owner falls outside the configured allowlist."""
        if self.allowed_owners and owner not in self.allowed_owners:
            allowed = ", ".join(self.allowed_owners)
            raise ValueError(f"Owner '{owner}' is outside the configured boundary: {allowed}")