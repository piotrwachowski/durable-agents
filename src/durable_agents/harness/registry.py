from __future__ import annotations

from typing import Any

from durable_agents.models import ToolEntry


class ToolRegistrationError(Exception):
    """Raised when a tool name is registered more than once."""


class ToolRegistry:
    """Module-level singleton registry mapping tool names to callables and schemas."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolEntry] = {}

    def register(self, entry: ToolEntry) -> None:
        """Register a tool entry. Raises ToolRegistrationError on duplicate name."""
        if entry.name in self._tools:
            raise ToolRegistrationError(
                f"Tool '{entry.name}' is already registered. "
                "Each tool name must be unique across the registry."
            )
        self._tools[entry.name] = entry

    def get(self, name: str) -> ToolEntry | None:
        """Return the ToolEntry for the given name, or None if not found."""
        return self._tools.get(name)

    def to_openai_tools(
        self, names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Return tool schemas in the OpenAI `tools=` format.

        If *names* is provided, only include tools with those names (preserving
        order).  If *names* is None, return all registered tools.
        """
        if names is None:
            entries = list(self._tools.values())
        else:
            entries = [self._tools[n] for n in names if n in self._tools]

        return [
            {
                "type": "function",
                "function": {
                    "name": entry.name,
                    "description": entry.description,
                    "parameters": entry.parameters,
                },
            }
            for entry in entries
        ]

    def get_callable(self, name: str) -> Any | None:
        """Return the raw callable for the given tool name, or None."""
        entry = self._tools.get(name)
        return entry.callable if entry else None

    def all_names(self) -> list[str]:
        """Return all registered tool names."""
        return list(self._tools.keys())


# Module-level singleton — populated by @tool at import time.
registry = ToolRegistry()
