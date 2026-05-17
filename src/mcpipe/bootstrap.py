"""Auto-discover and import all plugins and transforms.

Both CLI and MCP server call bootstrap() once at startup to populate
the tool and transform registries. No hardcoded imports needed anywhere.
"""

from __future__ import annotations

import importlib
import pkgutil

import mcpipe.plugins as _plugins_pkg
import mcpipe.transforms as _transforms_pkg
from mcpipe.cache import gc
from mcpipe.log import get_logger
from mcpipe.plugin import get_tools
from mcpipe.transform import get_transforms

# Import framework module to trigger @tool registration at import time.
__import__("mcpipe.framework")

_log = get_logger("bootstrap")


def bootstrap() -> None:
    """Import all plugins and transforms, triggering registration."""
    gc()

    # Built-in transforms (auto-discovered)
    for info in pkgutil.iter_modules(_transforms_pkg.__path__):
        importlib.import_module(f"mcpipe.transforms.{info.name}")
        _log.info("loaded transforms: %s", info.name)

    _log.info("transforms registered: %d", len(get_transforms()))

    # Plugin tools (auto-discovered)
    for info in pkgutil.iter_modules(_plugins_pkg.__path__):
        importlib.import_module(f"mcpipe.plugins.{info.name}")
        _log.info("loaded plugin: %s", info.name)

    _log.info("total tools registered: %d", len(get_tools()))
