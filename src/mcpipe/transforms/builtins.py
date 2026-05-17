"""Built-in transforms for mcpipe.

All registered as weak — user @transform with the same name replaces them.
"""

from __future__ import annotations

import re
from typing import Annotated

from mcpipe.transform import transform


@transform("Filter lines by regex pattern (case-insensitive)", weak=True)
def search(
    lines: list[str],
    pattern: Annotated[str, "Regex pattern to match"],
) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [line for line in lines if regex.search(line)]


@transform("Return at most N lines from the start", weak=True)
def limit(
    lines: list[str],
    n: Annotated[int, "Maximum number of lines"] = 50,
) -> list[str]:
    return lines[:n]


@transform("Skip the first N lines", weak=True)
def offset(
    lines: list[str],
    n: Annotated[int, "Number of lines to skip"] = 0,
) -> list[str]:
    return lines[n:]


@transform("Return the first N lines", weak=True)
def head(
    lines: list[str],
    n: Annotated[int, "Number of lines"] = 10,
) -> list[str]:
    return lines[:n]


@transform("Return the last N lines", weak=True)
def tail(
    lines: list[str],
    n: Annotated[int, "Number of lines"] = 10,
) -> list[str]:
    return lines[-n:] if n else lines
