"""Tests for the @tool decorator and its JSON-schema generation."""
from __future__ import annotations

from durable_agents.models import ToolEntry
from durable_agents.tools.decorators import tool


def test_tool_generates_schema_from_type_hints() -> None:
    @tool
    async def sample_tool_a(query: str, limit: int = 5) -> str:
        """Search docstring."""
        return "ok"

    entry: ToolEntry = sample_tool_a.__tool_entry__  # type: ignore[attr-defined]
    assert isinstance(entry, ToolEntry)
    assert entry.name == "sample_tool_a"
    assert entry.description == "Search docstring."

    params = entry.parameters
    assert params["type"] == "object"
    assert params["properties"]["query"] == {"type": "string"}
    assert params["properties"]["limit"] == {"type": "integer"}
    # Only the parameter without a default is required.
    assert params["required"] == ["query"]


def test_tool_unknown_type_falls_back_to_string() -> None:
    @tool
    async def sample_tool_d(payload: object) -> str:
        """Takes an exotic type."""
        return "ok"

    entry: ToolEntry = sample_tool_d.__tool_entry__  # type: ignore[attr-defined]
    assert entry.parameters["properties"]["payload"] == {"type": "string"}


def test_tool_options_are_stored_on_entry() -> None:
    @tool(timeout_seconds=30, max_retries=2)
    async def sample_tool_b(x: str) -> str:
        """B."""
        return x

    entry: ToolEntry = sample_tool_b.__tool_entry__  # type: ignore[attr-defined]
    assert entry.timeout_seconds == 30
    assert entry.max_retries == 2


def test_tool_defaults_have_no_options() -> None:
    @tool
    async def sample_tool_e(x: str) -> str:
        """E."""
        return x

    entry: ToolEntry = sample_tool_e.__tool_entry__  # type: ignore[attr-defined]
    assert entry.timeout_seconds is None
    assert entry.max_retries is None


async def test_tool_wrapper_remains_callable() -> None:
    @tool
    async def sample_tool_c(x: str) -> str:
        """C."""
        return x.upper()

    assert await sample_tool_c("hi") == "HI"
