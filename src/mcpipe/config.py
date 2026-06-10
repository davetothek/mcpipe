"""Configuration for mcpipe.

Resolution order (highest priority first):
  1. Environment variables (MCPIPE_*)
  2. Config file: $XDG_CONFIG_HOME/mcpipe/config.toml
  3. Compiled defaults

Config file format (all keys optional)::

    [cache]
    dir = "/custom/path"
    ttl = 7200
    inline_threshold = 100

    [authoring]
    enabled = true

    [paths]
    allowed = ["/home/user/projects", "/data"]
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# XDG helpers
# ---------------------------------------------------------------------------


def _xdg_config_home() -> Path:
    env = os.environ.get("XDG_CONFIG_HOME")
    return Path(env) if env else Path.home() / ".config"


def _xdg_runtime_dir() -> Path | None:
    env = os.environ.get("XDG_RUNTIME_DIR")
    return Path(env) if env else None


def _default_cache_dir() -> Path:
    """Per-user cache directory.  Prefer XDG_RUNTIME_DIR (tmpfs)."""
    runtime = _xdg_runtime_dir()
    if runtime:
        return runtime / "mcpipe"
    return Path(f"/tmp/mcpipe-{os.getuid()}")


# ---------------------------------------------------------------------------
# Settings dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CacheSettings:
    dir: Path = field(default_factory=_default_cache_dir)
    ttl: int = 3600
    inline_threshold: int = 50


@dataclass(slots=True)
class AuthoringSettings:
    enabled: bool = False


@dataclass(slots=True)
class PathSettings:
    """Allowed filesystem roots for the filesystem plugin.

    Paths are resolved to absolute form and validated on load.
    An empty list means "CWD only" (the default).
    """

    allowed: list[Path] = field(default_factory=list)

    def get_roots(self) -> list[Path]:
        """Return allowed roots, falling back to CWD if none configured."""
        if self.allowed:
            return [p.resolve() for p in self.allowed]
        return [Path.cwd().resolve()]

    def validate_path(self, path: Path) -> Path:
        """Resolve *path* and verify it falls under an allowed root.

        Raises:
            ValueError: If path escapes all allowed roots.
        """
        resolved = path.resolve()
        for root in self.get_roots():
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        roots_str = ", ".join(str(r) for r in self.get_roots())
        raise ValueError(
            f"Path '{resolved}' is outside allowed roots: {roots_str}"
        )


@dataclass(slots=True)
class Config:
    cache: CacheSettings = field(default_factory=CacheSettings)
    authoring: AuthoringSettings = field(default_factory=AuthoringSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    config_home: Path = field(
        default_factory=lambda: _xdg_config_home() / "mcpipe",
    )

    @property
    def user_plugins_dir(self) -> Path:
        return self.config_home / "plugins"

    @property
    def user_transforms_dir(self) -> Path:
        return self.config_home / "transforms"

    def ensure_user_dirs(self) -> None:
        """Create user plugin/transform directories if they don't exist."""
        self.user_plugins_dir.mkdir(parents=True, exist_ok=True)
        self.user_transforms_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_config: Config | None = None


def get_config() -> Config:
    """Return the global config, loading on first access."""
    global _config
    if _config is None:
        _config = _load()
    return _config


def _reset() -> None:
    """Clear cached config.  For testing only."""
    global _config
    _config = None


def _load() -> Config:
    cfg = Config()
    _apply_toml(cfg)
    _apply_env(cfg)
    return cfg


def _apply_toml(cfg: Config) -> None:
    toml_path = cfg.config_home / "config.toml"
    if not toml_path.is_file():
        return
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    cache = data.get("cache", {})
    if "dir" in cache:
        cfg.cache.dir = Path(cache["dir"])
    if "ttl" in cache:
        cfg.cache.ttl = int(cache["ttl"])
    if "inline_threshold" in cache:
        cfg.cache.inline_threshold = int(cache["inline_threshold"])

    authoring = data.get("authoring", {})
    if "enabled" in authoring:
        cfg.authoring.enabled = bool(authoring["enabled"])

    paths = data.get("paths", {})
    if "allowed" in paths:
        cfg.paths.allowed = [Path(p).resolve() for p in paths["allowed"]]


def _apply_env(cfg: Config) -> None:
    if v := os.environ.get("MCPIPE_CACHE_DIR"):
        cfg.cache.dir = Path(v)
    if v := os.environ.get("MCPIPE_CACHE_TTL"):
        cfg.cache.ttl = int(v)
    if v := os.environ.get("MCPIPE_INLINE_THRESHOLD"):
        cfg.cache.inline_threshold = int(v)
    if os.environ.get("MCPIPE_ENABLE_AUTHORING") == "1":
        cfg.authoring.enabled = True
    if v := os.environ.get("FS_ROOTS"):
        cfg.paths.allowed = [Path(p).resolve() for p in v.split(":") if p]
