# gh-for-zush

GitHub-backed zush group wrapper.

This package is not a zush extension. It builds a zush root group with GitHub management commands embedded into zush's reserved `self` surface by passing host-owned `system_commands` to `create_zush_group(...)`.

Current surface:

- `create_ghzush_group(...)` mirrors zush's root-group factory and returns a zush group
- `GhConfig` sets the default owner, owner boundary, and command templates
- Host-owned `self install`, `self update`, `self uninstall`, `self status`, `self sources`, `self search`, and `self available`
- `self search` uses the GitHub CLI search surface through `zuu.v202602_1.gh.search_repositories(...)`
- `main.py` constructs `GhConfig(...)` directly and appends wrapper prefixes
- When only `allowed_owners` is preset, the first allowed owner becomes the effective default owner
- Repository result lists are rendered as tables
- When the wrapper passes `zush_config.env_prefix`, `self search` and `self available` filter repositories by those prefixes
- `self available` refreshes a cached preset-scoped inventory and `self status` reads that cache with installed-state checks
- `self available` uses cached inventory by default and supports `--refresh` to fetch again
- `self install`, `self update`, and `self uninstall` execute their rendered subprocess commands by default
- `self install`, `self update`, and `self uninstall` support lossy short names when the cached preset inventory makes the match unique
- `self update --all` updates every installed package that appears in the cached wrapper inventory
- `self uninstall` defaults to a non-interactive remove command: `pip uninstall {package} -y`
- `main.py --dry-run ...` strips the flag before Click parses argv and echoes commands instead of running them

Examples:

```powershell
uv run python main.py self sources
uv run python main.py self status
uv run python main.py self search zush --owner ZackaryW
uv run python main.py self install gh-for-zush
uv run python main.py self update --all
uv run python main.py self available
uv run python main.py self available --refresh
uv run python main.py self install jobqueue
uv run python main.py self uninstall jobqueue
uv run python main.py --dry-run self install jobqueue
```

Embedding example:

```python
from gh_for_zush import create_ghzush_group

app.add_command(create_ghzush_group(), "zush")
```

Factory parameters:

- `gh_config=` accepts `GhConfig`
- `zush_config=` accepts `zush.configparse.config.Config`
- `execute_command=` optionally replaces subprocess execution for host-controlled dry-run or tests
- `storage=` and `mock_path=` pass through to `create_zush_group(...)`

Repository entrypoint notes:

- `main.py` appends `pvt_`, `zush_`, `pvt-`, and `zush-` to `config.env_prefix`
- `main.py --dry-run ...` only changes command execution; it does not change repository resolution or cache reads

Boundary example:

```python
from gh_for_zush import GhConfig, create_ghzush_group

gh_config = GhConfig(
    default_owner="my-org",
    allowed_owners=("my-org",),
)

app.add_command(create_ghzush_group(gh_config=gh_config), "zush")
```

With that config:

- `self search <query>` defaults to `my-org`
- `self search <query> --owner other-org` is rejected
- `self install repo-name` resolves to `my-org/repo-name`
- `self install other-org/repo-name` is rejected
- `self available` lists repositories across the preset owner boundary
- `self status` reports cached packages with installed `yes` or `no`
- `self install jobqueue`, `self update jobqueue`, and `self uninstall jobqueue` resolve through cached preset matches when only one prefixed package fits
- `self update --all` updates installed cached packages without needing each name on the command line
- `self search` and `self available` can be narrowed by wrapper-defined repository prefixes such as `zush_`, `zush-`, `pvt_`, and `pvt-`
- `self uninstall` renders `pip uninstall <package> -y` unless you override `remove_cmd`

Search notes:

- `self search` requires the GitHub CLI (`gh`) to be installed and authenticated
- If `default_owner` is omitted but `allowed_owners` is preset, `self search` uses the first allowed owner
- If neither `default_owner` nor `allowed_owners` is configured, `self search` requires `--owner`
- If `zush_config.env_prefix` is present, repository names are filtered to those prefixes before list output is shown
- `self available` writes the filtered inventory to a wrapper cache file
- `self available` reads the wrapper cache by default and only refreshes live inventory with `--refresh`
- `self status` reads that cache and compares repository names against installed Python distributions visible to the current runtime

List formatting:

- `self search` renders repository matches in a table with `owner`, `name`, `updated_at`, and `description`
- `self available` renders the preset-scoped repository inventory in the same table format

Direct `main.py` example:

```powershell
uv run python main.py self search zush
```

```python
from gh_for_zush import GhConfig, create_ghzush_group

gh_config = GhConfig(default_owner="ZackaryW", allowed_owners=("ZackaryW", "Pathverse"))
cli = create_ghzush_group(name="gh-for-zush", gh_config=gh_config)
```
