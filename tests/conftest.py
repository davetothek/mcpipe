"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_config():
    """Reset cached config between tests."""
    from mcpipe.config import _reset

    _reset()
    yield
    _reset()


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Redirect cache to a temp directory."""
    monkeypatch.setenv("MCPIPE_CACHE_DIR", str(tmp_path))
    from mcpipe.config import _reset

    _reset()  # Reload config with new env
    return tmp_path
