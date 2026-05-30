"""Example 01 — Worker for the simple research agent.

    # Terminal 1 — Temporal server
    temporal server start-dev

    # Terminal 2 — Start the worker (blocks until Ctrl-C)
    uv run python examples/01_research_agent/worker.py

    # Terminal 3 — Submit a task
    uv run python examples/01_research_agent/client.py "What is quantum entanglement?"

The workflow appears in the Temporal UI at http://localhost:8233.
"""
from __future__ import annotations

import asyncio

from tools import summarise, web_search

from durable_agents import create_durable_agent

# create_durable_agent() is the worker-side factory.  Calling it registers the
# tools into the local ToolRegistry and stores the agent config so that
# activities can read them at execution time — no schemas cross the wire.
agent = create_durable_agent(
    model="openai:gpt-4o-mini",
    tools=[web_search, summarise],
    system_prompt=(
        "You are a helpful research assistant. "
        "Use the web_search tool to look up information before answering. "
        "After receiving search results, write a concise, well-structured answer."
    ),
    task_queue="research-agent",
    max_steps=10,
)


async def main() -> None:
    print("Worker starting on task queue 'research-agent' …")
    print("Temporal UI: http://localhost:8233")
    await agent.run_worker()


if __name__ == "__main__":
    asyncio.run(main())


