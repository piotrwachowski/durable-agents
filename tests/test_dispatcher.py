"""Tests for the dispatch_tool activity error/observation handling.

dispatch_tool is an @activity.defn but does not use the activity context, so it
can be awaited directly in tests.
"""
from __future__ import annotations

from durable_agents.activities.dispatcher import dispatch_tool
from durable_agents.tools.decorators import tool


@tool
async def disp_ok_tool(x: str) -> str:
    """Echo tool."""
    return f"got {x}"


@tool
async def disp_raise_tool(x: str) -> str:
    """Always raises."""
    raise ValueError("boom")


@tool
async def disp_dict_tool() -> dict:
    """Returns a non-string result."""
    return {"a": 1}


async def test_unknown_tool_returns_observation() -> None:
    out = await dispatch_tool("nope_tool", {})
    assert out.startswith("ERROR: tool 'nope_tool' is not registered")


async def test_successful_dispatch() -> None:
    assert await dispatch_tool("disp_ok_tool", {"x": "hi"}) == "got hi"


async def test_functions_prefix_is_stripped() -> None:
    assert await dispatch_tool("functions.disp_ok_tool", {"x": "hi"}) == "got hi"


async def test_tool_error_is_returned_as_observation() -> None:
    out = await dispatch_tool("disp_raise_tool", {"x": "hi"})
    assert "ERROR calling tool 'disp_raise_tool'" in out
    assert "ValueError" in out
    assert "boom" in out


async def test_non_string_result_is_json_encoded() -> None:
    out = await dispatch_tool("disp_dict_tool", {})
    assert out == '{"a": 1}'


async def test_none_args_are_tolerated() -> None:
    # A tool taking no required args can be called with None args.
    assert await dispatch_tool("disp_dict_tool", None) == '{"a": 1}'
