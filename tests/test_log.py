"""Tests for mcpipe.log."""

from __future__ import annotations

import logging

import pytest

from mcpipe.log import (
    TRACE,
    _Ansi,
    _DeltaFormatter,
    get_logger,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_delta_formatter_and_handlers():
    # Save original handlers
    root = logging.getLogger("mcpipe")
    orig_handlers = list(root.handlers)
    orig_level = root.level

    # Reset formatter state
    _DeltaFormatter._first = None

    yield

    # Restore
    _DeltaFormatter._first = None
    root.handlers.clear()
    for h in orig_handlers:
        root.addHandler(h)
    root.setLevel(orig_level)


def test_delta_formatter_color():
    formatter = _DeltaFormatter(use_color=True)

    # LogRecord 1 (first)
    record1 = logging.LogRecord(
        name="mcpipe.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="First message",
        args=(),
        exc_info=None,
    )
    record1.created = 1000000.0  # static time

    prefix1 = formatter._prefix(record1)
    assert _Ansi.GREY in prefix1
    assert _Ansi.RESET in prefix1

    formatted1 = formatter.format(record1)
    assert "First message" in formatted1
    assert _Ansi.GREY in formatted1

    # LogRecord 2 (delta of 75 seconds -> +00:01:15)
    record2 = logging.LogRecord(
        name="mcpipe.test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=12,
        msg="Second message",
        args=(),
        exc_info=None,
    )
    record2.created = 1000075.0

    prefix2 = formatter._prefix(record2)
    assert "+00:01:15" in prefix2

    # Level colors
    assert formatter._level_color(logging.CRITICAL) == _Ansi.BOLD_RED
    assert formatter._level_color(logging.ERROR) == _Ansi.RED
    assert formatter._level_color(logging.WARNING) == _Ansi.YELLOW
    assert formatter._level_color(logging.INFO) == ""
    assert formatter._level_color(logging.DEBUG) == _Ansi.CYAN
    assert formatter._level_color(TRACE) == _Ansi.BLUE


def test_delta_formatter_no_color():
    formatter = _DeltaFormatter(use_color=False)
    assert formatter._level_color(logging.CRITICAL) == ""

    # First record
    record1 = logging.LogRecord(
        name="mcpipe.test",
        level=logging.CRITICAL,
        pathname="test.py",
        lineno=10,
        msg="Fatal error",
        args=(),
        exc_info=None,
    )
    record1.created = 1000000.0

    prefix1 = formatter._prefix(record1)
    assert _Ansi.GREY not in prefix1

    formatted1 = formatter.format(record1)
    assert "[FTL] Fatal error" in formatted1

    # Second record (delta 10000 seconds -> +02:46:40)
    record2 = logging.LogRecord(
        name="mcpipe.test",
        level=TRACE,
        pathname="test.py",
        lineno=12,
        msg="Trace msg",
        args=(),
        exc_info=None,
    )
    record2.created = 1010000.0
    prefix2 = formatter._prefix(record2)
    assert "+02:46:40" in prefix2

    # Level tags
    assert formatter._level_tag(logging.CRITICAL) == "[FTL] "
    assert formatter._level_tag(logging.ERROR) == "[ERR] "
    assert formatter._level_tag(logging.WARNING) == "[WAR] "
    assert formatter._level_tag(logging.INFO) == "[INF] "
    assert formatter._level_tag(logging.DEBUG) == "[DBG] "
    assert formatter._level_tag(TRACE) == "[TRC] "


def test_setup_logging():
    # Test setting different verbosities
    for verbosity, expected_level in [
        (0, logging.WARNING),
        (1, logging.INFO),
        (2, logging.DEBUG),
        (3, TRACE),
    ]:
        setup_logging(verbosity=verbosity, color=True)
        root = logging.getLogger("mcpipe")
        assert root.level == expected_level
        assert len(root.handlers) == 1
        formatter = root.handlers[0].formatter
        assert isinstance(formatter, _DeltaFormatter)
        assert formatter._color is True

    # Check color=False
    setup_logging(verbosity=0, color=False)
    root = logging.getLogger("mcpipe")
    formatter = root.handlers[0].formatter
    assert isinstance(formatter, _DeltaFormatter)
    assert formatter._color is False


def test_get_logger():
    logger = get_logger("my_plugin")
    assert logger.name == "mcpipe.my_plugin"
