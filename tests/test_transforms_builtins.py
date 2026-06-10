"""Tests for mcpipe.transforms.builtins."""

from __future__ import annotations

from mcpipe.transforms.builtins import head, limit, offset, search, tail


def test_search():
    lines = ["apple", "Banana", "Cherry", "apricot"]
    assert search(lines, "ap") == ["apple", "apricot"]
    assert search(lines, "BAN") == ["Banana"]
    assert search(lines, "xyz") == []


def test_limit():
    lines = ["a", "b", "c", "d"]
    assert limit(lines, 2) == ["a", "b"]
    assert limit(lines, 10) == ["a", "b", "c", "d"]
    assert limit(lines) == ["a", "b", "c", "d"]  # default is 50


def test_offset():
    lines = ["a", "b", "c", "d"]
    assert offset(lines, 2) == ["c", "d"]
    assert offset(lines, 0) == ["a", "b", "c", "d"]
    assert offset(lines) == ["a", "b", "c", "d"]  # default is 0


def test_head():
    lines = ["a", "b", "c", "d"]
    assert head(lines, 2) == ["a", "b"]
    assert head(lines) == ["a", "b", "c", "d"]  # default is 10


def test_tail():
    lines = ["a", "b", "c", "d"]
    assert tail(lines, 2) == ["c", "d"]
    assert tail(lines, 0) == ["a", "b", "c", "d"]
    assert tail(lines) == ["a", "b", "c", "d"]  # default is 10
