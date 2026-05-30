"""Code Archaeologist — Worker entry point.

Starts four Temporal workers in parallel, one per agent task queue:

    code-archaeologist   — orchestrator
    archaeologist-agent  — analyses legacy code
    modernizer-agent     — rewrites code to modern idioms
    documenter-agent     — adds docstrings and README

Usage::

    # Terminal 1 — Start the Temporal server
    temporal server start-dev

    # Terminal 2 — Start all four workers (blocks until Ctrl-C)
    uv run python examples/03_code_archaeologist/worker.py

    # Terminal 3 — Submit a task
    uv run python examples/03_code_archaeologist/client.py

All four workflows are visible in the Temporal UI at http://localhost:8233.
The modernizer and documenter appear as child workflows of the orchestrator.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the examples/ directory importable when running with `uv run python`.
sys.path.insert(0, str(Path(__file__).parent))

from agents import (
    archaeologist_agent,
    documenter_agent,
    modernizer_agent,
    orchestrator_agent,
)

_TASK_QUEUES = [
    "code-archaeologist",
    "archaeologist-agent",
    "modernizer-agent",
    "documenter-agent",
]


async def main() -> None:
    print("Code Archaeologist — starting workers")
    print()
    print("Task queues:")
    for q in _TASK_QUEUES:
        print(f"  • {q}")
    print()
    print("Temporal UI: http://localhost:8233")
    print()
    print("Press Ctrl-C to stop.")

    await asyncio.gather(
        orchestrator_agent.run_worker(),
        archaeologist_agent.run_worker(),
        modernizer_agent.run_worker(),
        documenter_agent.run_worker(),
    )


if __name__ == "__main__":
    asyncio.run(main())
