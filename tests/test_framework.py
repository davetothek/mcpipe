"""Tests for mcpipe.framework — paginate, search, handles tool functions."""

from __future__ import annotations

from mcpipe.cache import store
from mcpipe.framework import handles, paginate, search


class TestPaginate:
    def test_basic_slice(self, tmp_cache):
        handle = store("t", "a\nb\nc\nd\ne")
        result = paginate(handle=handle, offset=1, limit=2)
        assert "lines 1-2 of 5" in result
        assert "b" in result
        assert "c" in result

    def test_offset_beyond_end(self, tmp_cache):
        handle = store("t", "a\nb")
        result = paginate(handle=handle, offset=100, limit=5)
        assert "No lines at offset 100" in result

    def test_missing_handle(self, tmp_cache):
        result = paginate(handle="nonexistent_xyz", offset=0, limit=10)
        assert "Error" in result


class TestSearch:
    def test_finds_matches(self, tmp_cache):
        handle = store("t", "foo bar\nbaz\nfoo qux")
        result = search(handle=handle, pattern="foo")
        assert "2 matches" in result
        assert "foo bar" in result
        assert "foo qux" in result

    def test_no_matches(self, tmp_cache):
        handle = store("t", "aaa\nbbb")
        result = search(handle=handle, pattern="zzz")
        assert "No matches" in result

    def test_missing_handle(self, tmp_cache):
        result = search(handle="nonexistent_xyz", pattern="x")
        assert "Error" in result


class TestHandles:
    def test_lists_active(self, tmp_cache):
        h1 = store("a", "x")
        h2 = store("b", "y")
        result = handles()
        assert h1 in result
        assert h2 in result

    def test_empty(self, tmp_cache):
        result = handles()
        assert "No cached outputs" in result
