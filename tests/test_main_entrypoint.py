"""Tests for mcpipe.__main__."""

from __future__ import annotations

from unittest.mock import patch

from mcpipe.__main__ import cli


def test_cli_entrypoint():
    with patch("asyncio.run", return_value=0) as mock_run:
        with patch("sys.exit") as mock_exit:
            cli()
            mock_run.assert_called_once()
            mock_exit.assert_called_once_with(0)
