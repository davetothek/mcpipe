"""Tests for mcpipe.authoring."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import mcpipe.authoring as authoring_mod
from mcpipe.authoring import (
    _validate_code,
    authoring_help,
    delete_plugin,
    delete_transform,
    list_user_extensions,
    read_extension,
    write_plugin,
    write_transform,
)


def test_validate_code_syntax_error():
    with pytest.raises(ValueError) as exc:
        _validate_code("def foo(:")
    assert "Syntax error in Python code" in str(exc.value)


def test_validate_code_forbidden_imports():
    # Test ast.Import
    for banned in [
        "os",
        "subprocess",
        "shutil",
        "socket",
        "requests",
        "urllib",
        "builtins",
        "importlib",
        "sys",
    ]:
        with pytest.raises(ValueError) as exc:
            _validate_code(f"import {banned}")
        assert f"Import of forbidden module: {banned}" in str(exc.value)

    # Test ast.ImportFrom
    for banned in ["os", "subprocess", "sys"]:
        with pytest.raises(ValueError) as exc:
            _validate_code(f"from {banned} import path")
        assert f"Import from forbidden module: {banned}" in str(exc.value)

    # Test nested package imports
    with pytest.raises(ValueError) as exc:
        _validate_code("import os.path")
    assert "Import of forbidden module: os.path" in str(exc.value)


def test_validate_code_forbidden_calls():
    # exec, eval, compile, __import__
    for fn in ["exec", "eval", "compile", "__import__"]:
        with pytest.raises(ValueError) as exc:
            _validate_code(f"x = {fn}('print(1)')")
        assert f"Call to forbidden function: {fn}()" in str(exc.value)

    # Test attribute calls e.g. foo.exec()
    with pytest.raises(ValueError) as exc:
        _validate_code("foo.eval(1)")
    assert "Call to forbidden function: eval()" in str(exc.value)


def test_validate_code_success():
    # Valid and safe imports / function calls
    safe_code = """
import math
from typing import Annotated
from mcpipe import tool

@tool("Safe tool")
def safe_fn(x: int = 1) -> str:
    print(math.sqrt(x))
    return "ok"
"""
    _validate_code(safe_code)


def test_authoring_help():
    p_help = authoring_help(topic="plugin")
    assert "# mcpipe Plugin Authoring Guide" in p_help

    t_help = authoring_help(topic="transform")
    assert "# mcpipe Transform Authoring Guide" in t_help

    both_help = authoring_help(topic="both")
    assert "# mcpipe Plugin Authoring Guide" in both_help
    assert "# mcpipe Transform Authoring Guide" in both_help


@pytest.fixture
def mock_config_dirs(tmp_path, monkeypatch):
    mock_cfg = MagicMock()
    mock_cfg.user_plugins_dir = tmp_path / "plugins"
    mock_cfg.user_transforms_dir = tmp_path / "transforms"

    # Mock ensure_user_dirs
    def ensure():
        mock_cfg.user_plugins_dir.mkdir(parents=True, exist_ok=True)
        mock_cfg.user_transforms_dir.mkdir(parents=True, exist_ok=True)

    mock_cfg.ensure_user_dirs = ensure

    monkeypatch.setattr(authoring_mod, "get_config", lambda: mock_cfg)
    return mock_cfg


def test_list_user_extensions(mock_config_dirs):
    # Dirs don't exist yet
    res = json.loads(list_user_extensions())
    assert res["plugins"] == []
    assert res["transforms"] == []

    # Create dirs and files
    mock_config_dirs.ensure_user_dirs()

    (mock_config_dirs.user_plugins_dir / "plugin_a.py").write_text("# code")
    (mock_config_dirs.user_plugins_dir / "_ignored.py").write_text("# code")
    (mock_config_dirs.user_transforms_dir / "trans_b.py").write_text("# code")
    (mock_config_dirs.user_transforms_dir / "_ignored.py").write_text("# code")

    res2 = json.loads(list_user_extensions())
    assert res2["plugins"] == ["plugin_a.py"]
    assert res2["transforms"] == ["trans_b.py"]


def test_read_extension(mock_config_dirs):
    # Not found
    res = read_extension("nonexistent", kind="plugin")
    assert "Error:" in res

    # Create and read plugin
    mock_config_dirs.ensure_user_dirs()
    (mock_config_dirs.user_plugins_dir / "my_plug.py").write_text(
        "print('hello')", encoding="utf-8"
    )
    assert read_extension("my_plug", kind="plugin") == "print('hello')"

    # Create and read transform
    (mock_config_dirs.user_transforms_dir / "my_trans.py").write_text(
        "print('world')", encoding="utf-8"
    )
    assert read_extension("my_trans", kind="transform") == "print('world')"


def test_write_plugin(mock_config_dirs):
    content = "def foo(): pass"

    # 1. Create
    res1 = write_plugin("new_plug", content)
    assert "created" in res1
    path = mock_config_dirs.user_plugins_dir / "new_plug.py"
    assert path.read_text() == content

    # 2. Update
    res2 = write_plugin("new_plug", "def foo(): return 1")
    assert "updated" in res2
    assert path.read_text() == "def foo(): return 1"


def test_write_transform(mock_config_dirs):
    content = "def foo(): pass"

    # 1. Create
    res1 = write_transform("new_trans", content)
    assert "created" in res1
    path = mock_config_dirs.user_transforms_dir / "new_trans.py"
    assert path.read_text() == content

    # 2. Update
    res2 = write_transform("new_trans", "def foo(): return 1")
    assert "updated" in res2
    assert path.read_text() == "def foo(): return 1"


def test_delete_plugin(mock_config_dirs):
    # Delete non-existent
    res = delete_plugin("missing")
    assert "Error:" in res

    # Delete existing
    mock_config_dirs.ensure_user_dirs()
    path = mock_config_dirs.user_plugins_dir / "my_plug.py"
    path.write_text("# code")

    res2 = delete_plugin("my_plug")
    assert "deleted" in res2
    assert not path.exists()


def test_delete_transform(mock_config_dirs):
    # Delete non-existent
    res = delete_transform("missing")
    assert "Error:" in res

    # Delete existing
    mock_config_dirs.ensure_user_dirs()
    path = mock_config_dirs.user_transforms_dir / "my_trans.py"
    path.write_text("# code")

    res2 = delete_transform("my_trans")
    assert "deleted" in res2
    assert not path.exists()
