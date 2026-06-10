"""Tests for mcpipe.transform."""

from __future__ import annotations

import logging
import sys
from typing import Annotated

import pytest

from mcpipe.transform import (
    TransformStep,
    _clear_transforms,
    _resolve_positional,
    apply_transforms,
    get_transforms,
    transform,
)

transform_module = sys.modules["mcpipe.transform"]


@pytest.fixture
def clean_transforms():
    """Backup the transform registry and restore it after the test."""
    original = dict(transform_module._REGISTRY)
    transform_module._REGISTRY.clear()

    import logging

    logger = logging.getLogger("mcpipe")
    orig_level = logger.level
    logger.setLevel(logging.DEBUG)

    yield

    logger.setLevel(orig_level)
    transform_module._REGISTRY.clear()
    transform_module._REGISTRY.update(original)


def test_get_transforms(clean_transforms):
    assert get_transforms() == {}

    @transform("A test transform")
    def dummy(lines: list[str]) -> list[str]:
        return lines

    assert "dummy" in get_transforms()


def test_clear_transforms(clean_transforms):
    @transform("A test transform")
    def dummy(lines: list[str]) -> list[str]:
        return lines

    assert "dummy" in get_transforms()
    removed = _clear_transforms()
    assert removed == {"dummy"}
    assert get_transforms() == {}


def test_transform_decorator_registration(clean_transforms, caplog):
    with caplog.at_level(logging.DEBUG):

        @transform("Upper cases all lines")
        def uppercase(lines: list[str]) -> list[str]:
            return [line.upper() for line in lines]

    assert "uppercase" in get_transforms()
    entry = get_transforms()["uppercase"]
    assert entry.description == "Upper cases all lines"
    assert entry.func == uppercase
    assert "registered transform 'uppercase'" in caplog.text


def test_transform_decorator_override(clean_transforms, caplog):
    @transform("Original")
    def dummy(lines: list[str]) -> list[str]:
        return lines

    with caplog.at_level(logging.INFO):

        @transform("Overridden")
        def dummy(lines: list[str]) -> list[str]:
            return [line + "!" for line in lines]

    assert "dummy" in get_transforms()
    entry = get_transforms()["dummy"]
    assert entry.description == "Overridden"
    assert "transform 'dummy' overridden" in caplog.text


def test_resolve_positional_coercion(clean_transforms):
    @transform("Test coercion")
    def my_transform(
        lines: list[str],
        val_int: int,
        val_float: float,
        val_bool: bool,
        val_str: str,
    ) -> list[str]:
        return lines

    entry = get_transforms()["my_transform"]

    # All values as strings initially
    params = {
        "val_int": "123",
        "val_float": "4.56",
        "val_bool": "yes",
        "val_str": "hello",
    }
    resolved = _resolve_positional(params, entry)
    assert resolved["val_int"] == 123
    assert resolved["val_float"] == 4.56
    assert resolved["val_bool"] is True
    assert resolved["val_str"] == "hello"

    # Test boolean coercion variants
    for true_val in ("true", "1", "yes"):
        assert _resolve_positional({"val_bool": true_val}, entry)["val_bool"] is True
    for false_val in ("false", "0", "no", "anything"):
        assert _resolve_positional({"val_bool": false_val}, entry)["val_bool"] is False

    # Test non-string values passed directly (should not be coerced/changed)
    params_direct = {
        "val_int": 999,
        "val_float": 1.2,
        "val_bool": False,
    }
    resolved_direct = _resolve_positional(params_direct, entry)
    assert resolved_direct["val_int"] == 999
    assert resolved_direct["val_float"] == 1.2
    assert resolved_direct["val_bool"] is False


def test_resolve_positional_shorthand(clean_transforms):
    # Case 1: has required params
    @transform("Shorthand test 1")
    def trans_req(
        lines: list[str],
        x: Annotated[int, "first required param"],
        y: int = 10,
    ) -> list[str]:
        return lines

    entry_req = get_transforms()["trans_req"]
    params = {"_positional": "42"}
    resolved = _resolve_positional(params, entry_req)
    assert (
        resolved["x"] == 42
    )  # Coerced to int and assigned to 'x' (the required parameter)
    assert "_positional" not in resolved

    # Case 2: no required params, targets the first parameter in properties
    @transform("Shorthand test 2")
    def trans_noreq(
        lines: list[str],
        a: int = 5,
        b: str = "ok",
    ) -> list[str]:
        return lines

    entry_noreq = get_transforms()["trans_noreq"]
    params = {"_positional": "99"}
    resolved = _resolve_positional(params, entry_noreq)
    assert resolved["a"] == 99
    assert "_positional" not in resolved

    # Case 3: no parameters at all
    @transform("Shorthand test 3")
    def trans_noparams(lines: list[str]) -> list[str]:
        return lines

    entry_noparams = get_transforms()["trans_noparams"]
    params = {"_positional": "ignored"}
    resolved = _resolve_positional(params, entry_noparams)
    assert "_positional" not in resolved


def test_apply_transforms_success(clean_transforms):
    @transform("First")
    def first(lines: list[str], suffix: str = "") -> list[str]:
        return [line + suffix for line in lines]

    @transform("Second")
    def second(lines: list[str], prefix: str = "") -> list[str]:
        return [prefix + line for line in lines]

    steps = [
        TransformStep(name="first", params={"suffix": "!"}),
        TransformStep(name="second", params={"prefix": ">> "}),
    ]

    result = apply_transforms(["a", "b"], steps)
    assert result == [">> a!", ">> b!"]


def test_apply_transforms_unknown(clean_transforms):
    # When registry is empty
    steps = [TransformStep(name="nonexistent", params={})]
    with pytest.raises(ValueError) as exc_info:
        apply_transforms(["a"], steps)
    assert "Unknown transform: 'nonexistent'. Available: (none)" in str(exc_info.value)

    # When registry is not empty
    @transform("Some")
    def dummy(lines: list[str]) -> list[str]:
        return lines

    with pytest.raises(ValueError) as exc_info:
        apply_transforms(["a"], steps)
    assert "Unknown transform: 'nonexistent'. Available: dummy" in str(exc_info.value)


def test_apply_transforms_invalid_args(clean_transforms):
    @transform("With param")
    def my_trans(lines: list[str], expected_int: int) -> list[str]:
        return lines

    # Passing invalid parameter type (raises TypeError/ValueError)
    steps = [TransformStep(name="my_trans", params={"unexpected_arg": "value"})]
    with pytest.raises(ValueError) as exc_info:
        apply_transforms(["a"], steps)

    assert "Transform 'my_trans':" in str(exc_info.value)
    assert "Known params: expected_int" in str(exc_info.value)
    assert "Available transforms: my_trans" in str(exc_info.value)

    @transform("No params")
    def no_param_trans(lines: list[str]) -> list[str]:
        return lines

    steps = [TransformStep(name="no_param_trans", params={"unexpected_arg": "value"})]
    with pytest.raises(ValueError) as exc_info:
        apply_transforms(["a"], steps)
    assert "Known params: (none)" in str(exc_info.value)
