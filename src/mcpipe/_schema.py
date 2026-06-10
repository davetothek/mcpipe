"""Shared JSON Schema generation from function signatures.

Used by both the @tool and @transform decorators to build input schemas
from type hints and Annotated metadata.
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Annotated, Any, get_type_hints

_PY_TO_JSON: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def build_schema(
    func: Callable,
    *,
    skip: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Generate JSON Schema from function signature + type hints.

    Args:
        func: The function to introspect.
        skip: Parameter names to exclude from the schema.
    """
    hints = get_type_hints(func, include_extras=True)
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name in skip:
            continue

        hint = hints.get(name, str)
        description = None

        # Unwrap Annotated[type, "description"]
        origin = typing.get_origin(hint)
        if origin is Annotated:
            args = typing.get_args(hint)
            hint = args[0]
            for meta in args[1:]:
                if isinstance(meta, str):
                    description = meta
                    break

        json_type = _PY_TO_JSON.get(hint, "string")
        prop: dict[str, Any] = {"type": json_type}
        if description:
            prop["description"] = description
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(name)

        properties[name] = prop

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
