"""Security tests for mcpipe — cache handle validation, authoring guardrails."""

from __future__ import annotations

import pytest

from mcpipe.authoring import _validate_code
from mcpipe.cache import load


class TestCacheSecurity:
    def test_blocks_path_traversal(self, tmp_cache):
        with pytest.raises(ValueError, match="Invalid cache handle"):
            load("../../../etc/passwd")

    def test_blocks_shell_injection_chars(self, tmp_cache):
        with pytest.raises(ValueError, match="Invalid cache handle"):
            load("tool; rm -rf /")

    def test_allows_valid_handle(self, tmp_cache):
        # We need a file to exist for load() to not raise
        # FileNotFoundError after validation
        handle = "valid_handle_123.test-name"
        path = tmp_cache / handle
        path.write_text("data")
        meta = tmp_cache / f"{handle}.meta"
        meta.write_text("0\n3600\n")

        cached = load(handle)
        assert cached.handle == handle


class TestAuthoringSecurity:
    def test_blocks_banned_imports(self):
        code = "import os\ndef tool(): pass"
        with pytest.raises(ValueError, match="Import of forbidden module: os"):
            _validate_code(code)

    def test_blocks_from_imports(self):
        code = "from subprocess import Popen\ndef tool(): pass"
        with pytest.raises(
            ValueError,
            match="Import from forbidden module: subprocess",
        ):
            _validate_code(code)

    def test_blocks_nested_imports(self):
        code = "def tool():\n    import requests\n    return 'hi'"
        with pytest.raises(ValueError, match="Import of forbidden module: requests"):
            _validate_code(code)

    def test_blocks_importlib(self):
        code = "import importlib\ndef tool(): pass"
        with pytest.raises(ValueError, match="Import of forbidden module: importlib"):
            _validate_code(code)

    def test_blocks_sys(self):
        code = "import sys\ndef tool(): pass"
        with pytest.raises(ValueError, match="Import of forbidden module: sys"):
            _validate_code(code)

    def test_blocks_exec_call(self):
        code = "exec('import os')\ndef tool(): pass"
        with pytest.raises(ValueError, match="Call to forbidden function: exec"):
            _validate_code(code)

    def test_blocks_eval_call(self):
        code = "x = eval('1+1')\ndef tool(): pass"
        with pytest.raises(ValueError, match="Call to forbidden function: eval"):
            _validate_code(code)

    def test_blocks_dunder_import(self):
        code = "__import__('os')\ndef tool(): pass"
        with pytest.raises(ValueError, match="Call to forbidden function: __import__"):
            _validate_code(code)

    def test_blocks_compile_call(self):
        code = "compile('pass', '<string>', 'exec')\ndef tool(): pass"
        with pytest.raises(ValueError, match="Call to forbidden function: compile"):
            _validate_code(code)

    def test_allows_safe_imports(self):
        code = (
            "import json\nimport math\nfrom typing import Annotated\ndef tool(): pass"
        )
        # Should not raise
        _validate_code(code)

    def test_raises_on_syntax_error(self):
        code = "def tool(:"
        with pytest.raises(ValueError, match="Syntax error in Python code"):
            _validate_code(code)
