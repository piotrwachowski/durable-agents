from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, get_type_hints

from durable_agents.models import ToolEntry

# Deferred import to avoid circular dependency; registry populated at call time.
_REGISTRY: Any = None


def _get_registry() -> Any:
    global _REGISTRY
    if _REGISTRY is None:
        from durable_agents.harness.registry import registry as _reg
        _REGISTRY = _reg
    return _REGISTRY


# ── Type hint → JSON schema mapping ──────────────────────────────────────────

_TYPE_MAP: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_type_to_json_schema(annotation: Any) -> dict[str, Any]:
    """Convert a simple Python type annotation to a JSON schema fragment."""
    schema_type = _TYPE_MAP.get(annotation)
    if schema_type is not None:
        return {"type": schema_type}
    # Fall back to string for unrecognised types.
    return {"type": "string"}


def _build_parameters_schema(func: Callable[..., Any]) -> dict[str, Any]:
    """Derive a JSON schema `parameters` object from a function's type hints."""
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name == "return":
            continue
        annotation = hints.get(param_name, str)
        properties[param_name] = _python_type_to_json_schema(annotation)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


# ── @tool decorator ───────────────────────────────────────────────────────────

def tool(
    _func: Callable[..., Any] | None = None,
    *,
    timeout_seconds: int | None = None,
    max_retries: int | None = None,
) -> Any:
    """Decorator that registers an async function as a durable tool.

    Usage::

        @tool
        async def web_search(query: str) -> str: ...

        @tool(timeout_seconds=30, max_retries=2)
        async def slow_tool(url: str) -> str: ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        description = (func.__doc__ or "").strip()
        parameters = _build_parameters_schema(func)

        entry = ToolEntry(
            name=func.__name__,
            callable=func,
            description=description,
            parameters=parameters,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        _get_registry().register(entry)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        # Attach metadata for introspection.
        wrapper.__tool_entry__ = entry  # type: ignore[attr-defined]
        return wrapper

    if _func is not None:
        # Called as @tool (no arguments)
        return decorator(_func)
    # Called as @tool(...) with keyword arguments
    return decorator
