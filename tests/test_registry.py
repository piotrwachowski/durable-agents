"""Tests for the ToolRegistry."""
from __future__ import annotations

import pytest

from durable_agents.harness.registry import ToolRegistrationError, ToolRegistry
from durable_agents.models import ToolEntry


def _entry(name: str) -> ToolEntry:
    return ToolEntry(
        name=name,
        callable=lambda: None,
        description=f"description of {name}",
        parameters={"type": "object", "properties": {}},
    )


def test_register_and_get() -> None:
    r = ToolRegistry()
    e = _entry("a")
    r.register(e)
    assert r.get("a") is e
    assert r.all_names() == ["a"]


def test_get_missing_returns_none() -> None:
    r = ToolRegistry()
    assert r.get("missing") is None
    assert r.get_callable("missing") is None


def test_duplicate_registration_raises() -> None:
    r = ToolRegistry()
    r.register(_entry("a"))
    with pytest.raises(ToolRegistrationError):
        r.register(_entry("a"))


def test_to_openai_tools_filters_and_preserves_order() -> None:
    r = ToolRegistry()
    r.register(_entry("a"))
    r.register(_entry("b"))
    r.register(_entry("c"))

    selected = r.to_openai_tools(["c", "a"])
    names = [t["function"]["name"] for t in selected]
    assert names == ["c", "a"]
    # Schema shape is the OpenAI tools format.
    assert selected[0]["type"] == "function"
    assert "parameters" in selected[0]["function"]


def test_to_openai_tools_none_returns_all() -> None:
    r = ToolRegistry()
    r.register(_entry("a"))
    r.register(_entry("b"))
    names = {t["function"]["name"] for t in r.to_openai_tools()}
    assert names == {"a", "b"}


def test_to_openai_tools_ignores_unknown_names() -> None:
    r = ToolRegistry()
    r.register(_entry("a"))
    assert r.to_openai_tools(["a", "does-not-exist"]) == r.to_openai_tools(["a"])
