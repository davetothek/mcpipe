"""Tests for mcpipe.server — camelCase serialization, dispatch, handlers."""

from __future__ import annotations

import asyncio

from mcpipe.server import _camel, _dispatch, _handle_initialize, _to_json
from mcpipe.types.protocol import (
    ErrorCode,
    InitializeResult,
    ServerCapabilities,
    ServerInfo,
    TextContent,
    Tool,
    ToolAnnotations,
    ToolResult,
)

# ---------------------------------------------------------------------------
# _camel
# ---------------------------------------------------------------------------


class TestCamel:
    def test_single_word(self):
        assert _camel("name") == "name"

    def test_two_words(self):
        assert _camel("server_info") == "serverInfo"

    def test_three_words(self):
        assert _camel("protocol_version_number") == "protocolVersionNumber"

    def test_already_camel(self):
        # Single word — no underscores — passes through
        assert _camel("tools") == "tools"


# ---------------------------------------------------------------------------
# _to_json
# ---------------------------------------------------------------------------


class TestToJson:
    def test_initialize_result_camel_keys(self):
        result = InitializeResult(
            capabilities=ServerCapabilities(),
            server_info=ServerInfo(name="test", version="1.0"),
        )
        j = _to_json(result)
        assert "protocolVersion" in j
        assert "serverInfo" in j
        assert "server_info" not in j
        assert "protocol_version" not in j
        assert j["serverInfo"]["name"] == "test"

    def test_tool_annotations_camel(self):
        ann = ToolAnnotations(read_only=True, destructive=False, open_world=False)
        j = _to_json(ann)
        assert "readOnly" in j
        assert "openWorld" in j
        assert "read_only" not in j

    def test_tool_input_schema_camel(self):
        t = Tool(name="test", description="d", input_schema={"type": "object"})
        j = _to_json(t)
        assert "inputSchema" in j
        assert "input_schema" not in j

    def test_none_fields_omitted(self):
        t = Tool(name="t", description="d", output_schema=None)
        j = _to_json(t)
        assert "outputSchema" not in j

    def test_tool_result_camel(self):
        tr = ToolResult(
            content=[TextContent(text="hi")],
            is_error=False,
        )
        j = _to_json(tr)
        # is_error=False is not None, so it should be present as isError
        assert "isError" in j
        assert j["isError"] is False

    def test_list_of_dataclasses(self):
        items = [TextContent(text="a"), TextContent(text="b")]
        j = _to_json(items)
        assert j == [{"text": "a", "type": "text"}, {"text": "b", "type": "text"}]

    def test_plain_dict_passthrough(self):
        d = {"key": "value", "none_key": None}
        j = _to_json(d)
        # dict keys are NOT camelCased (only dataclass fields are)
        assert j == {"key": "value"}  # None removed


# ---------------------------------------------------------------------------
# _handle_initialize
# ---------------------------------------------------------------------------


class TestHandleInitialize:
    def test_response_structure(self):
        resp = _handle_initialize(req_id=1)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        result = resp["result"]
        assert "protocolVersion" in result
        assert "serverInfo" in result
        assert "capabilities" in result

    def test_protocol_version_is_string(self):
        resp = _handle_initialize(req_id=1)
        assert isinstance(resp["result"]["protocolVersion"], str)

    def test_server_info_has_name_version(self):
        resp = _handle_initialize(req_id=1)
        si = resp["result"]["serverInfo"]
        assert "name" in si
        assert "version" in si


# ---------------------------------------------------------------------------
# _dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_initialize(self):
        resp = asyncio.run(
            _dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        )
        assert resp is not None
        assert resp["result"]["protocolVersion"]

    def test_ping(self):
        resp = asyncio.run(
            _dispatch({"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}})
        )
        assert resp is not None
        assert resp["result"] == {}

    def test_unknown_method(self):
        resp = asyncio.run(
            _dispatch({"jsonrpc": "2.0", "id": 3, "method": "bogus", "params": {}})
        )
        assert resp is not None
        assert "error" in resp
        assert resp["error"]["code"] == ErrorCode.METHOD_NOT_FOUND.value

    def test_notification_returns_none(self):
        resp = asyncio.run(
            _dispatch({"method": "notifications/initialized", "params": {}})
        )
        assert resp is None

    def test_tools_list(self, tmp_cache):
        # Bootstrap to register tools
        from mcpipe.bootstrap import bootstrap

        bootstrap()
        resp = asyncio.run(
            _dispatch({"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}})
        )
        assert resp is not None
        tools = resp["result"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Check all tools have camelCase keys
        for t in tools:
            assert "inputSchema" in t
            assert "input_schema" not in t

    def test_tools_call_unknown_tool(self, tmp_cache):
        resp = asyncio.run(
            _dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "no_such_tool_xyz"},
                }
            )
        )
        assert resp is not None
        assert "error" in resp

    def test_tools_call_missing_name(self, tmp_cache):
        resp = asyncio.run(
            _dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {},
                }
            )
        )
        assert resp is not None
        assert "error" in resp


class TestServerHelpers:
    def test_inject_meta_params_no_param_transform(self, monkeypatch):
        from mcpipe.transform import _TransformEntry

        # Setup mock transform registry with 0-param transform
        mock_entry = _TransformEntry(
            func=lambda lines: lines,
            description="No param transform",
            param_schema={"properties": {}},
        )
        import mcpipe.server

        monkeypatch.setattr(
            mcpipe.server, "get_transforms", lambda: {"noparam": mock_entry}
        )

        schema = {"properties": {"arg": {"type": "string"}}}
        injected = mcpipe.server._inject_meta_params(schema)
        assert injected["properties"]["_noparam"]["type"] == "boolean"
        assert "No param transform" in injected["properties"]["_noparam"]["description"]

    def test_extract_transforms_all_cases(self):
        from mcpipe.server import _extract_transforms
        from mcpipe.transform import TransformStep

        args = {
            "_search": "hello",
            "_limit": "15",
            "_offset": "5",
            "_custom": "val",
            "normal": 42,
        }
        tool_args, steps = _extract_transforms(args)
        assert tool_args == {"normal": 42}
        assert steps == [
            TransformStep("search", {"pattern": "hello"}),
            TransformStep("limit", {"n": 15}),
            TransformStep("offset", {"n": 5}),
            TransformStep("custom", {"_positional": "val"}),
        ]

    def test_tool_output_to_result_inline(self):
        from mcpipe.plugin import ToolOutput
        from mcpipe.server import _tool_output_to_result

        out = ToolOutput(
            handle="h",
            total_lines=2,
            text="a\nb",
            preview=None,
            is_error=False,
        )
        res = _tool_output_to_result(out)
        assert res["isError"] is False
        assert res["content"] == [{"type": "text", "text": "a\nb"}]

    def test_tool_output_to_result_cached(self):
        from mcpipe.plugin import ToolOutput
        from mcpipe.server import _tool_output_to_result

        out = ToolOutput(
            handle="h",
            total_lines=2,
            text=None,
            preview="preview-lines",
            is_error=True,
        )
        res = _tool_output_to_result(out)
        assert res["isError"] is True
        text = res["content"][0]["text"]
        assert "Output cached as 'h'" in text
        assert "Preview:\npreview-lines" in text

        # Without preview
        out2 = ToolOutput(
            handle="h",
            total_lines=2,
            text=None,
            preview=None,
            is_error=False,
        )
        res2 = _tool_output_to_result(out2)
        assert "Preview:" not in res2["content"][0]["text"]

    def test_handle_tools_call_execution(self, monkeypatch):
        from mcpipe.plugin import ToolOutput
        from mcpipe.server import _handle_tools_call

        # Mock execute to return success
        async def mock_execute(name, tool_args, transforms=None):
            return ToolOutput("h", total_lines=1, text="ok")

        import mcpipe.server

        monkeypatch.setattr(mcpipe.server, "execute", mock_execute)

        # Test valid call
        resp = asyncio.run(
            _handle_tools_call(1, {"name": "view", "arguments": {"handle": "h"}})
        )
        assert resp["result"]["content"][0]["text"] == "ok"

        # Mock execute raising ValueError
        async def mock_execute_raise(name, tool_args, transforms=None):
            raise ValueError("Invalid value passed")

        monkeypatch.setattr(mcpipe.server, "execute", mock_execute_raise)
        resp2 = asyncio.run(
            _handle_tools_call(2, {"name": "view", "arguments": {"handle": "h"}})
        )
        assert "error" in resp2
        assert "Invalid value passed" in resp2["error"]["message"]

    def test_write_protocol(self):
        from unittest.mock import MagicMock

        from mcpipe.server import _WriteProtocol

        proto = _WriteProtocol()
        proto.connection_made(MagicMock())
        proto.connection_lost(None)

    def test_serve_unsupported_transport(self):
        import pytest

        from mcpipe.server import serve

        with pytest.raises(ValueError) as exc:
            asyncio.run(serve(transport="http"))
        assert "Unsupported transport" in str(exc.value)

    def test_serve_loop(self, monkeypatch):
        import json
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcpipe.server import serve

        # We will mock loop.connect_read_pipe and loop.connect_write_pipe
        # to simulate input lines and capture output.
        mock_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: mock_loop)

        mock_reader = AsyncMock()

        # Setup sequence of input lines:
        # 1. empty line (should be ignored)
        # 2. invalid JSON
        # 3. valid ping request
        # 4. EOF (empty bytes)
        mock_reader.readline.side_effect = [
            b"\n",
            b"not-json\n",
            b'{"jsonrpc": "2.0", "id": 42, "method": "ping"}\n',
            b"",
        ]

        # We patch StreamReaderProtocol to bind our mock_reader
        class FakeStreamReaderProtocol:
            def __init__(self, reader):
                pass

            def connection_made(self, transport):
                pass

        monkeypatch.setattr(asyncio, "StreamReader", lambda: mock_reader)
        monkeypatch.setattr(asyncio, "StreamReaderProtocol", FakeStreamReaderProtocol)

        mock_loop.connect_read_pipe = AsyncMock(
            return_value=(MagicMock(), FakeStreamReaderProtocol(None))
        )

        # Capture stdout writes
        written_data = []
        mock_transport = MagicMock()

        def write_bytes(data):
            written_data.append(data)

        mock_transport.write = write_bytes

        mock_loop.connect_write_pipe = AsyncMock(
            return_value=(mock_transport, MagicMock())
        )

        with patch("mcpipe.server.bootstrap") as mock_bootstrap:
            asyncio.run(serve())
            mock_bootstrap.assert_called_once()

        assert len(written_data) == 2
        # First write is parse error for "not-json"
        res1 = json.loads(written_data[0].decode().strip())
        assert "error" in res1
        assert res1["error"]["code"] == ErrorCode.PARSE_ERROR.value

        # Second write is success response for ping
        res2 = json.loads(written_data[1].decode().strip())
        assert res2["id"] == 42
        assert res2["result"] == {}
