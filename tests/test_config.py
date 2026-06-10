"""Tests for mcpipe.config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mcpipe.config import (
    Config,
    PathSettings,
    _apply_env,
    _apply_toml,
    _default_cache_dir,
    _load,
    _reset,
    _xdg_config_home,
    _xdg_runtime_dir,
    get_config,
)


def test_xdg_config_home(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/xdg/config")
    assert _xdg_config_home() == Path("/custom/xdg/config")

    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    # The default fallback uses Path.home() / ".config"
    assert _xdg_config_home() == Path.home() / ".config"


def test_xdg_runtime_dir(monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/custom/runtime")
    assert _xdg_runtime_dir() == Path("/custom/runtime")

    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert _xdg_runtime_dir() is None


def test_default_cache_dir(monkeypatch):
    # Case 1: XDG_RUNTIME_DIR is set
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/custom/runtime")
    assert _default_cache_dir() == Path("/custom/runtime/mcpipe")

    # Case 2: XDG_RUNTIME_DIR is not set
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    with patch("os.getuid", return_value=9999):
        assert _default_cache_dir() == Path("/tmp/mcpipe-9999")


def test_path_settings_get_roots(tmp_path):
    p = PathSettings()
    # When empty, returns CWD
    assert p.get_roots() == [Path.cwd().resolve()]

    # When not empty, returns resolved paths
    p.allowed = [Path("/tmp/some/../path")]
    assert p.get_roots() == [Path("/tmp/path").resolve()]


def test_path_settings_validate_path(tmp_path):
    p = PathSettings()
    # When empty (defaults to CWD)
    cwd = Path.cwd().resolve()
    # A path under CWD should be allowed
    inside_path = cwd / "some_file.txt"
    assert p.validate_path(inside_path) == inside_path

    # A path outside CWD should raise ValueError
    outside_path = cwd.parent.parent / "escaped_file.txt"
    with pytest.raises(ValueError) as exc_info:
        p.validate_path(outside_path)
    assert "is outside allowed roots:" in str(exc_info.value)

    # Let's test with custom roots
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"
    root1.mkdir()
    root2.mkdir()

    p.allowed = [root1, root2]
    # Path under root1
    assert p.validate_path(root1 / "foo") == (root1 / "foo").resolve()
    # Path under root2
    assert p.validate_path(root2 / "bar") == (root2 / "bar").resolve()
    # Path outside both
    with pytest.raises(ValueError):
        p.validate_path(tmp_path / "other")


def test_config_dirs(tmp_path):
    cfg = Config(config_home=tmp_path / "mcpipe")
    assert cfg.user_plugins_dir == tmp_path / "mcpipe" / "plugins"
    assert cfg.user_transforms_dir == tmp_path / "mcpipe" / "transforms"

    # Make sure they do not exist initially
    assert not cfg.user_plugins_dir.exists()
    assert not cfg.user_transforms_dir.exists()

    cfg.ensure_user_dirs()
    assert cfg.user_plugins_dir.is_dir()
    assert cfg.user_transforms_dir.is_dir()


def test_get_config_singleton():
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2

    _reset()
    cfg3 = get_config()
    assert cfg3 is not cfg1


def test_apply_toml_missing_file(tmp_path):
    cfg = Config(config_home=tmp_path)
    # File does not exist, should not raise, should keep default values
    _apply_toml(cfg)
    assert cfg.cache.ttl == 3600


def test_apply_toml_valid(tmp_path):
    cfg = Config(config_home=tmp_path)
    config_toml = tmp_path / "config.toml"
    config_toml.write_text(
        """
[cache]
dir = "/toml/cache"
ttl = 1800
inline_threshold = 25

[authoring]
enabled = true

[paths]
allowed = ["/toml/root1", "/toml/root2"]
        """
    )
    _apply_toml(cfg)
    assert cfg.cache.dir == Path("/toml/cache")
    assert cfg.cache.ttl == 1800
    assert cfg.cache.inline_threshold == 25
    assert cfg.authoring.enabled is True
    assert cfg.paths.allowed == [
        Path("/toml/root1").resolve(),
        Path("/toml/root2").resolve(),
    ]


def test_apply_env(monkeypatch):
    cfg = Config()
    monkeypatch.setenv("MCPIPE_CACHE_DIR", "/env/cache")
    monkeypatch.setenv("MCPIPE_CACHE_TTL", "999")
    monkeypatch.setenv("MCPIPE_INLINE_THRESHOLD", "42")
    monkeypatch.setenv("MCPIPE_ENABLE_AUTHORING", "1")
    monkeypatch.setenv("FS_ROOTS", "/env/root1:/env/root2:")

    _apply_env(cfg)
    assert cfg.cache.dir == Path("/env/cache")
    assert cfg.cache.ttl == 999
    assert cfg.cache.inline_threshold == 42
    assert cfg.authoring.enabled is True
    assert cfg.paths.allowed == [
        Path("/env/root1").resolve(),
        Path("/env/root2").resolve(),
    ]


def test_load_combines_defaults_toml_and_env(tmp_path, monkeypatch):
    # Set up config_home in a temp dir for TOML loading
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # We need to make sure config_home resolves to tmp_path / "mcpipe"
    config_home = tmp_path / "mcpipe"
    config_home.mkdir()

    # Write a config.toml
    config_toml = config_home / "config.toml"
    config_toml.write_text(
        """
[cache]
dir = "/toml/cache"
ttl = 1800

[authoring]
enabled = false
        """
    )

    # Now override some settings with env vars
    monkeypatch.setenv("MCPIPE_CACHE_TTL", "3000")
    monkeypatch.setenv("MCPIPE_ENABLE_AUTHORING", "1")

    cfg = _load()
    # Env overrides TOML
    assert cfg.cache.ttl == 3000
    # Env overrides TOML
    assert cfg.authoring.enabled is True
    # TOML value is preserved when not in env
    assert cfg.cache.dir == Path("/toml/cache")
    # Default is preserved when neither TOML nor env sets it
    assert cfg.cache.inline_threshold == 50
