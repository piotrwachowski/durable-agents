"""Tool definitions for the research-agent example.

Imported by worker.py and registered with the agent at startup. The client
never imports this module — it only needs the task queue name.
"""
from __future__ import annotations

from durable_agents import tool


@tool
async def web_search(query: str) -> str:
    """Search the web for information about the given query."""
    return (
        f"[stub] Search results for '{query}': "
        "Quantum entanglement is a phenomenon where two particles become "
        "correlated such that the quantum state of one particle cannot be "
        "described independently of the other, regardless of the distance "
        "separating them. (Source: stub)"
    )


@tool
async def summarise(text: str) -> str:
    """Produce a short summary of the given text."""
    words = text.split()
    short = " ".join(words[:40])
    return f"[stub summary] {short}{'…' if len(words) > 40 else ''}"
