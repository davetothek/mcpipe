"""File-based output cache for mcpipe.

Writes tool output to a per-user cache directory, manages handles and
TTL-based cleanup.  A handle is a descriptive key like
'git_log_1716000000000000000_a1b2c3d4' that both humans and LLMs can
reason about.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from mcpipe.log import get_logger

_log = get_logger("cache")

# Strict regex for cache handles to prevent path traversal and shell injection.
_HANDLE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _cache_dir() -> Path:
    from mcpipe.config import get_config

    return get_config().cache.dir


def _default_ttl() -> int:
    from mcpipe.config import get_config

    return get_config().cache.ttl


@dataclass(slots=True)
class CachedOutput:
    """A cached output loaded from disk."""

    handle: str
    lines: list[str]
    total_lines: int
    created_at: float

    def slice(self, offset: int = 0, limit: int = 50) -> list[str]:
        return self.lines[offset : offset + limit]

    def search(self, pattern: str) -> list[tuple[int, str]]:
        """Return (line_number, line) pairs matching the regex pattern."""
        regex = re.compile(pattern, re.IGNORECASE)
        return [(i, line) for i, line in enumerate(self.lines) if regex.search(line)]


def _ensure_dir() -> None:
    _cache_dir().mkdir(parents=True, exist_ok=True)


def store(tool_name: str, output: str, ttl: int | None = None) -> str:
    """Write output to cache. Returns the handle string."""
    _ensure_dir()
    ts_ns = time.time_ns()
    handle = f"{tool_name}_{ts_ns}_{uuid4().hex[:8]}"
    cache_dir = _cache_dir()
    path = cache_dir / handle
    path.write_text(output, encoding="utf-8")
    # Store TTL as xattr-like sidecar (simple approach)
    meta_path = cache_dir / f"{handle}.meta"
    ts = int(time.time())
    effective_ttl = ttl if ttl is not None else _default_ttl()
    meta_path.write_text(f"{ts}\n{effective_ttl}\n", encoding="utf-8")
    _log.debug(
        "stored %s (%d bytes, expires in %dm)",
        handle,
        len(output),
        effective_ttl // 60,
    )
    return handle


def load(handle: str) -> CachedOutput:
    """Load cached output by handle. Raises FileNotFoundError if missing."""
    if not _HANDLE_RE.fullmatch(handle):
        _log.warning("blocked invalid handle: %r", handle)
        raise ValueError(f"Invalid cache handle: {handle!r}")

    cache_dir = _cache_dir()
    path = cache_dir / handle
    if not path.exists():
        msg = f"No cached output for handle: {handle}"
        raise FileNotFoundError(msg)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    # Read creation time from meta
    meta_path = cache_dir / f"{handle}.meta"
    created_at = 0.0
    if meta_path.exists():
        parts = meta_path.read_text(encoding="utf-8").strip().split("\n")
        created_at = float(parts[0])
    _log.debug("loaded %s (%d lines)", handle, len(lines))
    return CachedOutput(
        handle=handle,
        lines=lines,
        total_lines=len(lines),
        created_at=created_at,
    )


def evict_expired() -> int:
    """Remove expired cache entries. Returns number of entries removed."""
    _ensure_dir()
    cache_dir = _cache_dir()
    now = time.time()
    removed = 0
    for meta_path in cache_dir.glob("*.meta"):
        parts = meta_path.read_text(encoding="utf-8").strip().split("\n")
        if len(parts) < 2:
            continue
        created, ttl = float(parts[0]), int(parts[1])
        if now - created > ttl:
            handle = meta_path.stem
            data_path = cache_dir / handle
            data_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            removed += 1
            _log.debug("evict: removed expired %s", handle)
    if removed:
        _log.info("evict: removed %d expired entries", removed)
    return removed


def list_handles() -> list[str]:
    """Return all active (non-expired) handles."""
    _ensure_dir()
    cache_dir = _cache_dir()
    now = time.time()
    handles: list[str] = []
    for meta_path in sorted(cache_dir.glob("*.meta")):
        parts = meta_path.read_text(encoding="utf-8").strip().split("\n")
        if len(parts) < 2:
            continue
        created, ttl = float(parts[0]), int(parts[1])
        if now - created <= ttl:
            handles.append(meta_path.stem)
    return handles
