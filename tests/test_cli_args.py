"""Tests for mcpipe.cli.args."""

from __future__ import annotations

import sys

import pytest

from mcpipe.cli.args import (
    Opts,
    _extract_transforms,
    _parse_tool_args,
    coerce_args,
    parse_argv,
)


class TestOptsColor:
    def test_always(self):
        opts = Opts(command="run", color="always")
        assert opts.use_color is True

    def test_never(self):
        opts = Opts(command="run", color="never")
        assert opts.use_color is False

    def test_auto_tty(self, monkeypatch):
        opts = Opts(command="run", color="auto")
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        assert opts.use_color is True

    def test_auto_non_tty(self, monkeypatch):
        opts = Opts(command="run", color="auto")
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        assert opts.use_color is False


class TestParseToolArgs:
    def test_various_formats(self):
        remainder = [
            "--",
            "--foo=bar",
            "--flag",
            "baz=qux",
            "--my-hyphen-arg=val",
        ]
        res = _parse_tool_args(remainder)
        assert res == {
            "foo": "bar",
            "flag": "true",
            "baz": "qux",
            "my_hyphen_arg": "val",
        }


class TestExtractTransforms:
    def test_no_transforms(self):
        argv, trans = _extract_transforms(["run", "tool", "a=1"])
        assert argv == ["run", "tool", "a=1"]
        assert trans == []

    def test_multiple_transforms(self):
        argv = [
            "run",
            "tool",
            "a=1",
            "-T",
            "search",
            "pattern=auth",
            "case=false",
            "--transform",
            "limit=10",
        ]
        rem_argv, trans = _extract_transforms(argv)
        assert rem_argv == ["run", "tool", "a=1"]
        assert trans == [
            ("search", {"pattern": "auth", "case": "false"}),
            ("limit", {"_positional": "10"}),
        ]

    def test_empty_T_at_end(self):
        argv = ["run", "tool", "-T"]
        rem_argv, trans = _extract_transforms(argv)
        assert rem_argv == ["run", "tool"]
        assert trans == []


class TestParseArgv:
    def test_no_command_raises_system_exit(self, capsys):
        with pytest.raises(SystemExit) as exc:
            parse_argv([])
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Plugin-based MCP server framework" in captured.out

    def test_run_command(self):
        opts = parse_argv(["run", "git_log", "since=1week", "-T", "head=5"])
        assert opts.command == "run"
        assert opts.tool == "git_log"
        assert opts.tool_args == {"since": "1week"}
        assert opts.transforms == [("head", {"_positional": "5"})]

    def test_view_command(self):
        opts = parse_argv(["view", "handle_123", "-T", "tail=10"])
        assert opts.command == "view"
        assert opts.handle == "handle_123"
        assert opts.transforms == [("tail", {"_positional": "10"})]

    def test_list_command(self):
        opts = parse_argv(["list", "git", "-p", "git_plugin", "--tools-only"])
        assert opts.command == "list"
        assert opts.filter == "git"
        assert opts.plugin_filter == "git_plugin"
        assert opts.tools_only is True
        assert opts.transforms_only is False

        opts2 = parse_argv(["list", "--transforms-only"])
        assert opts2.transforms_only is True

    def test_server_command(self):
        opts = parse_argv(["server", "--transport", "stdio"])
        assert opts.command == "server"
        assert opts.transport == "stdio"

    def test_run_command_remainder(self):
        # Additional positional args mapped as tool arguments
        opts = parse_argv(["run", "git_log", "--", "since=1week", "author=dev"])
        assert opts.tool_args == {"since": "1week", "author": "dev"}


class TestCoerceArgs:
    def test_coerce_all_types(self):
        schema = {
            "properties": {
                "val_int": {"type": "integer"},
                "val_float": {"type": "number"},
                "val_bool": {"type": "boolean"},
                "val_str": {"type": "string"},
            }
        }
        raw = {
            "val_int": "123",
            "val_float": "4.56",
            "val_bool": "yes",
            "val_str": "hello",
            "val_extra": "untyped",
        }
        coerced = coerce_args("dummy", raw, schema)
        assert coerced["val_int"] == 123
        assert coerced["val_float"] == 4.56
        assert coerced["val_bool"] is True
        assert coerced["val_str"] == "hello"
        assert coerced["val_extra"] == "untyped"

        # Check boolean false values
        assert (
            coerce_args("d", {"v": "0"}, {"properties": {"v": {"type": "boolean"}}})[
                "v"
            ]
            is False
        )
