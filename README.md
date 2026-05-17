# mcpipe

![license](https://img.shields.io/badge/license-MIT-blue)
![coverage](https://img.shields.io/badge/coverage-46%25-yellow)

<!--toc:start-->
- [How it works](#how-it-works)
- [Install](#install)
- [Usage](#usage)
  - [MCP server (for LLM clients)](#mcp-server-for-llm-clients)
  - [CLI](#cli)
- [Built-in plugins](#built-in-plugins)
  - [Git](#git)
  - [Docker](#docker)
  - [Docker Compose](#docker-compose)
  - [Filesystem](#filesystem)
- [Transforms](#transforms)
- [Writing plugins](#writing-plugins)
  - [Fuller example — git log](#fuller-example-git-log)
  - [Default output filters](#default-output-filters)
  - [Opting out of meta-params](#opting-out-of-meta-params)
- [LLM self-authoring](#llm-self-authoring)
  - [How it works](#how-it-works)
  - [Example: LLM creates a kubectl plugin](#example-llm-creates-a-kubectl-plugin)
- [Development](#development)
- [License](#license)
<!--toc:end-->

Plugin-based MCP server that keeps CLI output out of your context window.

Any command-line tool can be exposed as an MCP tool. Output gets cached to disk —
the LLM gets back a handle and uses generic framework tools (`view`, `search`) to
read what it needs instead of having the full dump shoved into the conversation.

Zero dependencies. Python 3.12+.

## How it works

```
LLM calls:  git_log(since="1week")
Returns:    { handle: "git_log_1716000000", lines: 847, preview: "..." }

LLM calls:  view(handle="git_log_1716000000", _search="auth")
Returns:    matching lines only
```

One tool produces. Generic tools consume. Plugins don't implement search or pagination.

## Install

```bash
uv pip install .
```

## Usage

### MCP server (for LLM clients)

```bash
mcpipe server
```

Speaks JSON-RPC 2.0 over stdio. Point your MCP client at it.

### CLI

```bash
mcpipe run git_log since="1 week ago"
mcpipe run docker_ps all=true
mcpipe view <handle> -T search pattern="error"
mcpipe list
```

## Built-in plugins

### Git

`git_status`, `git_log`, `git_diff`, `git_diff_unstaged`, `git_diff_staged`,
`git_show`, `git_branch`, `git_add`, `git_commit`, `git_reset`,
`git_create_branch`, `git_checkout`, `git_fetch`, `git_pull`, `git_push`,
`git_stash_push`, `git_stash_pop`, `git_stash_list`, `git_tag`,
`git_blame`, `git_cherry_pick`, `git_revert`, `git_remote`, `git_merge`

### Docker

`docker_ps`, `docker_logs`, `docker_images`

### Docker Compose

`compose_ps`, `compose_logs`, `compose_up`, `compose_down`, `compose_restart`,
`compose_stop`, `compose_start`, `compose_config`, `compose_top`,
`compose_images`, `compose_pull`, `compose_build`, `compose_exec`, `compose_run`

### Filesystem

`fs_read`, `fs_ls`, `fs_stat`, `fs_find`, `fs_grep`, `fs_roots`,
`fs_write`, `fs_mkdir`, `fs_rm`, `fs_mv`, `fs_cp`

Access is restricted to allowed directory trees. Set `FS_ROOTS` to a colon-separated
list of paths, or leave it unset to allow only the working directory.

## Transforms

Output post-processing is pluggable. Transforms are pure functions — lines in, lines out.

Built-in: `search`, `limit`, `offset`, `head`, `tail`.

Any tool call can include transform meta-params prefixed with `_`:

```json
{ "name": "git_log", "arguments": { "since": "1week", "_search": "fix", "_limit": 10 } }
```

Custom transforms use the `@transform` decorator:

```python
from mcpipe import transform

@transform("Sort lines alphabetically")
def sort(lines: list[str], reverse: bool = False) -> list[str]:
    return sorted(lines, reverse=reverse)
```

## Writing plugins

A plugin is a Python file in `mcpipe/plugins/` (built-in) or `~/.config/mcpipe/plugins/` (user).

```python
from typing import Annotated
from mcpipe import Cmd, tool

@tool("List running containers", read_only=True, destructive=False, idempotent=True)
def docker_ps(
    all: Annotated[bool, "Show all containers (including stopped)"] = False,
    format: Annotated[str, "Go template for output format"] = "",
) -> Cmd:
    args = ["docker", "ps"]
    if all:
        args.append("--all")
    if format:
        args.extend(["--format", format])
    return Cmd(*args)
```

Return `Cmd` to run a subprocess, or `str` for direct output. Type hints generate
the MCP input schema automatically. Use `Annotated[type, "description"]` to add
descriptions to parameters — these appear in the tool's JSON Schema.

Tool arguments are passed directly as keyword arguments to the function.
String values are sanitized first (`~` and `$ENV` expanded).

### Fuller example — git log

A more complete example showing a helper function, input validation, and
how `Annotated` args map to the subprocess call:

```python
from typing import Annotated
from mcpipe import Cmd, tool

def _git(*args: str, repo_path: str = ".") -> Cmd:
    """Build a git Cmd with -C repo_path prefix."""
    return Cmd("git", "-C", repo_path, *args)

def _validate_ref(value: str, label: str = "value") -> None:
    """Reject refs starting with '-' to prevent flag injection."""
    if value.startswith("-"):
        raise ValueError(f"Invalid {label}: '{value}' — cannot start with '-'")

@tool("Show commit log", read_only=True, destructive=False, idempotent=True)
def git_log(
    repo_path: Annotated[str, "Path to the git repository"] = ".",
    max_count: Annotated[int, "Number of commits to show"] = 10,
    since: Annotated[str, "Show commits after this date (e.g. '1 week ago')"] = "",
    path: Annotated[str, "Limit to commits touching this path"] = "",
) -> Cmd:
    args = ["log", f"--max-count={max_count}"]
    if since:
        _validate_ref(since, "since")
        args.extend(["--since", since])
    if path:
        _validate_ref(path, "path")
        args.extend(["--", path])
    return _git(*args, repo_path=repo_path)
```

When an LLM calls `git_log(max_count=5, since="1 week ago")`, this builds
and runs: `git -C . log --max-count=5 --since '1 week ago'`.

### Default output filters

Tools can declare default transforms that apply when the caller doesn't send any
`_meta` params. Useful for keeping verbose output short by default:

```python
from mcpipe import Cmd, tool
from mcpipe.transform import TransformStep

@tool(
    "Push commits to remote",
    read_only=False,
    output_filter=[TransformStep("head", {"n": 10})],
)
def git_push(...) -> Cmd:
    ...
```

Caller-provided transforms replace defaults entirely — no merging.

### Opting out of meta-params

By default, every tool gets transform meta-params (`_search`, `_limit`, etc.) injected
into its schema. Tools that shouldn't be filtered (config, help, authoring) can opt out:

```python
@tool("Show help text", read_only=True, meta_params=False)
def my_help() -> str:
    return "..."
```

## LLM self-authoring

An LLM connected to mcpipe can create its own tools and transforms at runtime —
no restarts, no manual file editing. This is the core design: if a tool doesn't
exist yet, the LLM writes it, reloads, and uses it immediately.

### How it works

mcpipe exposes framework tools for managing user extensions:

| Tool | Purpose |
|------|---------|
| `authoring_help` | Returns the full plugin/transform API guide |
| `write_plugin` | Creates or overwrites a user plugin file |
| `write_transform` | Creates or overwrites a user transform file |
| `read_extension` | Reads a user plugin/transform source file |
| `list_user_extensions` | Lists files in the user config dirs |
| `delete_plugin` / `delete_transform` | Removes a file |
| `reload` | Hot-reloads all modules to pick up changes |

User extensions live in `~/.config/mcpipe/` (or `$XDG_CONFIG_HOME/mcpipe/`):
- `plugins/*.py` — tools
- `transforms/*.py` — output transforms

### Example: LLM creates a kubectl plugin

```
User: "I need to check my Kubernetes pods"

LLM:  1. Calls authoring_help(topic="plugin") — reads the API
      2. Calls write_plugin(name="kubectl", content="...")
      3. Calls reload() — new tools are live
      4. Calls kubectl_get_pods(namespace="production")
      5. Calls view(handle="...", _search="CrashLoopBackOff")
```

The plugin persists across sessions. Next time the LLM connects, `kubectl_get_pods`
is already available.

## Development

```bash
uv run poe hooks    # install git hooks
uv run poe check    # lint + typecheck + tests
uv run poe test     # tests only
uv run poe lint     # ruff
uv run poe format   # ruff format
```

## License

MIT
