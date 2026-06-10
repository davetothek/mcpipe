"""Tests for mcpipe.cli.main."""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from mcpipe.cache import CachedOutput
from mcpipe.cli.main import main
from mcpipe.plugin import ToolOutput


def test_main_parse_argv_system_exit(capsys):
    # Empty argv prints help and exits
    code = asyncio.run(main([]))
    assert code == 1
    captured = capsys.readouterr()
    assert "Plugin-based MCP server framework" in captured.out


def test_main_run_unknown_tool(capsys):
    with patch("mcpipe.cli.main.get_tools", return_value={}):
        code = asyncio.run(main(["run", "nonexistent"]))
        assert code == 1
        captured = capsys.readouterr()
        assert "Error: unknown tool 'nonexistent'" in captured.err


def test_main_run_inline_success(capsys):
    mock_tool_entry = MagicMock()
    mock_tool_entry.tool.input_schema = {"properties": {}}

    mock_output = ToolOutput(
        handle="h",
        total_lines=1,
        text="some inline text",
        is_error=False,
    )

    with patch("mcpipe.cli.main.get_tools", return_value={"mytool": mock_tool_entry}):
        with patch("mcpipe.cli.main.execute", AsyncMock(return_value=mock_output)):
            code = asyncio.run(main(["run", "mytool"]))
            assert code == 0
            captured = capsys.readouterr()
            assert captured.out == "some inline text"


def test_main_run_cached_success(capsys):
    mock_tool_entry = MagicMock()
    mock_tool_entry.tool.input_schema = {"properties": {}}

    mock_output = ToolOutput(
        handle="my_handle_123",
        total_lines=100,
        text=None,
        preview="first few lines",
        is_error=False,
    )

    with patch("mcpipe.cli.main.get_tools", return_value={"mytool": mock_tool_entry}):
        with patch("mcpipe.cli.main.execute", AsyncMock(return_value=mock_output)):
            code = asyncio.run(main(["run", "mytool", "-T", "limit=5"]))
            assert code == 0
            captured = capsys.readouterr()
            assert "handle:  my_handle_123" in captured.out
            assert "lines:   100" in captured.out
            assert "preview:\nfirst few lines" in captured.out


def test_main_run_error_result(capsys):
    mock_tool_entry = MagicMock()
    mock_tool_entry.tool.input_schema = {"properties": {}}

    mock_output = ToolOutput(
        handle="h",
        total_lines=0,
        text="Some error content",
        is_error=True,
    )

    with patch("mcpipe.cli.main.get_tools", return_value={"mytool": mock_tool_entry}):
        with patch("mcpipe.cli.main.execute", AsyncMock(return_value=mock_output)):
            code = asyncio.run(main(["run", "mytool"]))
            assert code == 1
            captured = capsys.readouterr()
            assert "Some error content" in captured.err


def test_main_run_value_error(capsys):
    mock_tool_entry = MagicMock()
    mock_tool_entry.tool.input_schema = {"properties": {}}

    with patch("mcpipe.cli.main.get_tools", return_value={"mytool": mock_tool_entry}):
        with patch(
            "mcpipe.cli.main.execute", AsyncMock(side_effect=ValueError("Bad args"))
        ):
            code = asyncio.run(main(["run", "mytool"]))
            assert code == 1
            captured = capsys.readouterr()
            assert "Error: Bad args" in captured.err


def test_main_view_missing_handle(capsys):
    with patch("mcpipe.cache.load", side_effect=FileNotFoundError()):
        code = asyncio.run(main(["view", "nonexistent_handle"]))
        assert code == 1
        captured = capsys.readouterr()
        assert "Error: no cached output for handle 'nonexistent_handle'" in captured.err


def test_main_view_success_with_transforms(capsys):
    cached = CachedOutput(
        handle="h",
        lines=["line 1", "line 2", "line 3"],
        total_lines=3,
        created_at=0,
    )
    with patch("mcpipe.cache.load", return_value=cached):
        with patch(
            "mcpipe.cli.main.apply_transforms", return_value=["line 2", "line 3"]
        ) as mock_apply:
            code = asyncio.run(main(["view", "h", "-T", "offset=1"]))
            assert code == 0
            captured = capsys.readouterr()
            assert captured.out == "line 2\nline 3"
            mock_apply.assert_called_once()


def test_main_view_transform_error(capsys):
    cached = CachedOutput(
        handle="h",
        lines=["line 1"],
        total_lines=1,
        created_at=0,
    )
    with patch("mcpipe.cache.load", return_value=cached):
        with patch(
            "mcpipe.cli.main.apply_transforms", side_effect=ValueError("Bad transform")
        ):
            code = asyncio.run(main(["view", "h", "-T", "limit=invalid"]))
            assert code == 1
            captured = capsys.readouterr()
            assert "Error: Bad transform" in captured.err


def test_main_list_all(capsys):
    tool_entry_a = MagicMock()
    tool_entry_a.plugin = "git"
    tool_entry_a.tool.description = "Git status tool"

    tool_entry_b = MagicMock()
    tool_entry_b.plugin = "docker"
    tool_entry_b.tool.description = "Docker ps tool"

    mock_transform_entry = MagicMock()
    mock_transform_entry.description = "Search filter"

    with patch(
        "mcpipe.cli.main.get_tools",
        return_value={"git_status": tool_entry_a, "docker_ps": tool_entry_b},
    ):
        with patch(
            "mcpipe.transform.get_transforms",
            return_value={"search": mock_transform_entry},
        ):
            code = asyncio.run(main(["list"]))
            assert code == 0
            captured = capsys.readouterr()

            # Tools section
            assert "Tools" in captured.out
            assert "[git]" in captured.out
            assert "git_status" in captured.out
            assert "[docker]" in captured.out
            assert "docker_ps" in captured.out

            # Transforms section
            assert "Transforms" in captured.out
            assert "search" in captured.out


def test_main_list_filters(capsys):
    tool_entry_a = MagicMock()
    tool_entry_a.plugin = "git"
    tool_entry_a.tool.description = "Git status"

    mock_transform_entry = MagicMock()
    mock_transform_entry.description = "Search filter"

    with patch("mcpipe.cli.main.get_tools", return_value={"git_status": tool_entry_a}):
        with patch(
            "mcpipe.transform.get_transforms",
            return_value={"search": mock_transform_entry},
        ):
            # Filter by plugin
            code = asyncio.run(main(["list", "-p", "git"]))
            assert code == 0
            captured = capsys.readouterr()
            assert "[git]" in captured.out

            # Filter by plugin but not matched
            code = asyncio.run(main(["list", "-p", "docker"]))
            assert code == 0
            captured = capsys.readouterr()
            assert "[git]" not in captured.out

            # Filter by name substring
            code = asyncio.run(main(["list", "status"]))
            assert code == 0
            captured = capsys.readouterr()
            assert "git_status" in captured.out
            assert "search" not in captured.out


def test_main_list_tools_only_and_transforms_only(capsys):
    tool_entry_a = MagicMock()
    tool_entry_a.plugin = "git"
    tool_entry_a.tool.description = "Git status"

    mock_transform_entry = MagicMock()
    mock_transform_entry.description = "Search filter"

    with patch("mcpipe.cli.main.get_tools", return_value={"git_status": tool_entry_a}):
        with patch(
            "mcpipe.transform.get_transforms",
            return_value={"search": mock_transform_entry},
        ):
            # Tools only
            code = asyncio.run(main(["list", "--tools-only"]))
            assert code == 0
            captured = capsys.readouterr()
            assert "Tools" in captured.out
            assert "Transforms" not in captured.out

            # Transforms only
            code = asyncio.run(main(["list", "--transforms-only"]))
            assert code == 0
            captured = capsys.readouterr()
            assert "Tools" not in captured.out
            assert "Transforms" in captured.out

            # No matching tools (filter with something that doesn't match)
            code = asyncio.run(main(["list", "nonexistent", "--tools-only"]))
            assert code == 0
            captured = capsys.readouterr()
            assert "No matching tools." in captured.out


def test_main_server_command():
    with patch("mcpipe.server.serve", AsyncMock()) as mock_serve:
        code = asyncio.run(main(["server", "--transport", "stdio"]))
        assert code == 0
        mock_serve.assert_called_once_with(transport="stdio")


def test_main_sys_argv_fallback(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mcpipe", "list", "--tools-only"])

    with patch("mcpipe.cli.main.get_tools", return_value={}):
        code = asyncio.run(main())
        assert code == 0
