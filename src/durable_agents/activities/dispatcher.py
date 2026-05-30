from __future__ import annotations

import json
from typing import Any

from temporalio import activity

from durable_agents.harness.registry import registry

# Maximum bytes returned from a tool call — prevents oversized activity payloads.
_MAX_OUTPUT_BYTES = 50 * 1024  # 50 KB


@activity.defn
async def dispatch_tool(tool_name: str, tool_args: dict[str, Any] | None) -> str:
    """Look up a registered tool by name and call it with the provided arguments.

    Returns the tool's string output, truncated to 50 KB if needed.
    """
    # The LLM sometimes prefixes tool names with "functions." — strip it.
    if tool_name.startswith("functions."):
        tool_name = tool_name[len("functions."):]

    callable_ = registry.get_callable(tool_name)
    if callable_ is None:
        # Don't crash the workflow — return an observation so the LLM can pick a
        # valid tool on the next turn.
        return (
            f"ERROR: tool '{tool_name}' is not registered. "
            f"Available tools: {registry.all_names()}"
        )

    kwargs: dict[str, Any] = tool_args or {}
    try:
        raw_result = await callable_(**kwargs)
    except Exception as exc:  # noqa: BLE001 -- surface ALL tool errors to the LLM
        # A tool failing on bad arguments (e.g. a hallucinated file path) is an
        # expected outcome in an agent loop, not an infrastructure failure.
        # Return the error as an observation so the model can recover on the
        # next turn instead of failing the activity (which would crash the
        # workflow after retries).
        return f"ERROR calling tool '{tool_name}': {type(exc).__name__}: {exc}"

    # Normalise to string.
    if isinstance(raw_result, str):
        result = raw_result
    else:
        result = json.dumps(raw_result)

    # Truncate large outputs.
    encoded = result.encode("utf-8")
    if len(encoded) > _MAX_OUTPUT_BYTES:
        truncated = encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
        result = truncated + "\n[output truncated]"

    return result
