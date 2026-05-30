"""Example 01 — Thin client for the simple research agent.

Requires the worker (worker.py) and Temporal server to be running.

    uv run python examples/01_research_agent/client.py "What is quantum entanglement?"

DurableAgentClient only needs the task queue name — no tool imports required.
"""
from __future__ import annotations

import asyncio
import sys

from durable_agents import DurableAgentClient


async def main(task: str) -> None:
    print(f"Task: {task!r}")
    print("Workflow visible at http://localhost:8233\n")
    client = DurableAgentClient(task_queue="research-agent")
    result = await client.run(task)
    print("=== Result ===")
    print(result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: uv run python examples/01_research_agent/client.py "<task>"')
        sys.exit(1)
    asyncio.run(main(" ".join(sys.argv[1:])))
