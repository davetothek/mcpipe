"""Tests for mcpipe.bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

bootstrap_mod = sys.modules["mcpipe.bootstrap"]


@pytest.fixture
def clean_bootstrap():
    """Backup sys.modules, _loaded_modules, and registries to prevent leaks."""
    import sys

    plugin_mod = sys.modules["mcpipe.plugin"]
    transform_mod = sys.modules["mcpipe.transform"]

    orig_sys_modules = dict(sys.modules)
    orig_loaded = dict(bootstrap_mod._loaded_modules)
    orig_tools = dict(plugin_mod._REGISTRY)
    orig_transforms = dict(transform_mod._REGISTRY)

    yield

    sys.modules.clear()
    sys.modules.update(orig_sys_modules)
    bootstrap_mod._loaded_modules.clear()
    bootstrap_mod._loaded_modules.update(orig_loaded)
    plugin_mod._REGISTRY.clear()
    plugin_mod._REGISTRY.update(orig_tools)
    transform_mod._REGISTRY.clear()
    transform_mod._REGISTRY.update(orig_transforms)


def test_discover_and_load(clean_bootstrap):
    mock_package = MagicMock()
    mock_package.__path__ = ["/dummy/path"]

    # Module info mock
    class DummyInfo:
        def __init__(self, name):
            self.name = name

    # Mock iter_modules to return ['dummy_mod']
    with patch("pkgutil.iter_modules", return_value=[DummyInfo("dummy_mod")]):
        with patch("importlib.import_module") as mock_import:
            from types import ModuleType

            mock_mod = ModuleType("dummy_mod")
            mock_import.return_value = mock_mod

            # 1. First load
            loaded = bootstrap_mod._discover_and_load(mock_package, "my_prefix")
            assert loaded == ["dummy_mod"]
            mock_import.assert_called_once_with("my_prefix.dummy_mod")
            assert bootstrap_mod._loaded_modules["my_prefix.dummy_mod"] == mock_mod

            # 2. Reloading
            mock_import.reset_mock()
            with patch.object(bootstrap_mod.importlib, "reload") as mock_reload:
                loaded_reload = bootstrap_mod._discover_and_load(
                    mock_package, "my_prefix", reload=True
                )
                assert loaded_reload == ["dummy_mod"]
                mock_import.assert_not_called()
                mock_reload.assert_called_once_with(mock_mod)


def test_discover_user_dir_not_a_dir(clean_bootstrap):
    assert bootstrap_mod._discover_user_dir(Path("/nonexistent/dir"), "prefix") == []


def test_discover_user_dir_success(clean_bootstrap, tmp_path):
    # Setup test plugin file
    plugin_file = tmp_path / "my_user_plugin.py"
    plugin_file.write_text("# test plugin code")

    # Setup ignored plugin file
    ignored_file = tmp_path / "_ignored.py"
    ignored_file.write_text("# ignored code")

    mock_spec = MagicMock()
    mock_loader = MagicMock()
    mock_spec.loader = mock_loader
    mock_mod = MagicMock()

    with patch(
        "importlib.util.spec_from_file_location", return_value=mock_spec
    ) as mock_spec_from:
        with patch(
            "importlib.util.module_from_spec", return_value=mock_mod
        ) as mock_mod_from:
            loaded = bootstrap_mod._discover_user_dir(tmp_path, "mcpipe_user")
            assert loaded == ["my_user_plugin"]
            mock_spec_from.assert_called_once_with(
                "mcpipe_user.my_user_plugin", plugin_file
            )
            mock_mod_from.assert_called_once_with(mock_spec)
            mock_loader.exec_module.assert_called_once_with(mock_mod)
            assert (
                bootstrap_mod._loaded_modules["mcpipe_user.my_user_plugin"] == mock_mod
            )
            assert sys.modules["mcpipe_user.my_user_plugin"] == mock_mod


def test_discover_user_dir_bad_spec(clean_bootstrap, tmp_path):
    plugin_file = tmp_path / "bad_plugin.py"
    plugin_file.write_text("# code")

    with patch("importlib.util.spec_from_file_location", return_value=None):
        loaded = bootstrap_mod._discover_user_dir(tmp_path, "mcpipe_user")
        assert loaded == []


def test_discover_user_dir_exec_failed(clean_bootstrap, tmp_path, caplog):
    plugin_file = tmp_path / "error_plugin.py"
    plugin_file.write_text("# code")

    mock_spec = MagicMock()
    mock_loader = MagicMock()
    mock_spec.loader = mock_loader
    mock_mod = MagicMock()
    mock_loader.exec_module.side_effect = Exception("Compile error")

    with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
        with patch("importlib.util.module_from_spec", return_value=mock_mod):
            loaded = bootstrap_mod._discover_user_dir(tmp_path, "mcpipe_user")
            assert loaded == []
            assert "mcpipe_user.error_plugin" not in sys.modules
            assert any("failed to load" in record.message for record in caplog.records)


def test_bootstrap_authoring_disabled(clean_bootstrap, monkeypatch):
    # Ensure config has authoring disabled
    mock_cfg = MagicMock()
    mock_cfg.authoring.enabled = False
    mock_cfg.user_transforms_dir = Path("/tmp/transforms")
    mock_cfg.user_plugins_dir = Path("/tmp/plugins")
    monkeypatch.setattr(bootstrap_mod, "get_config", lambda: mock_cfg)

    with patch("mcpipe.bootstrap.evict_expired") as mock_evict:
        with patch("mcpipe.bootstrap._discover_and_load") as mock_discover_pkg:
            with patch("mcpipe.bootstrap._discover_user_dir") as mock_discover_user:
                bootstrap_mod.bootstrap()

                mock_evict.assert_called_once()
                # authoring tools should not be imported
                assert mock_discover_pkg.call_count == 2  # transforms and plugins
                assert mock_discover_user.call_count == 2


def test_bootstrap_authoring_enabled(clean_bootstrap, monkeypatch):
    # Ensure config has authoring enabled
    mock_cfg = MagicMock()
    mock_cfg.authoring.enabled = True
    mock_cfg.user_transforms_dir = Path("/tmp/transforms")
    mock_cfg.user_plugins_dir = Path("/tmp/plugins")
    monkeypatch.setattr(bootstrap_mod, "get_config", lambda: mock_cfg)

    with patch("mcpipe.bootstrap.evict_expired"):
        with patch("mcpipe.bootstrap._discover_and_load"):
            with patch("mcpipe.bootstrap._discover_user_dir"):
                with patch("builtins.__import__") as mock_import:
                    bootstrap_mod.bootstrap()
                    # Verify mcpipe.authoring is imported
                    mock_import.assert_any_call("mcpipe.authoring")


def test_reload_plugins(clean_bootstrap, monkeypatch):
    mock_cfg = MagicMock()
    mock_cfg.authoring.enabled = True
    mock_cfg.user_transforms_dir = Path("/tmp/transforms")
    mock_cfg.user_plugins_dir = Path("/tmp/plugins")
    monkeypatch.setattr(bootstrap_mod, "get_config", lambda: mock_cfg)

    with patch("mcpipe.bootstrap._discover_and_load") as mock_discover_pkg:
        with patch("mcpipe.bootstrap._discover_user_dir") as mock_discover_user:
            with patch("mcpipe.bootstrap._clear_plugin_tools") as mock_clear_tools:
                with patch("mcpipe.bootstrap._clear_transforms") as mock_clear_trans:
                    summary = bootstrap_mod.reload_plugins()

                    mock_clear_tools.assert_called_once()
                    mock_clear_trans.assert_called_once()
                    # Ensure reload=True is passed
                    mock_discover_pkg.assert_any_call(
                        bootstrap_mod._transforms_pkg,
                        "mcpipe.transforms",
                        reload=True,
                    )
                    mock_discover_user.assert_any_call(
                        mock_cfg.user_transforms_dir,
                        "mcpipe_user.transforms",
                        reload=True,
                    )
                    assert isinstance(summary, dict)
                    assert "tools" in summary
                    assert "transforms" in summary
