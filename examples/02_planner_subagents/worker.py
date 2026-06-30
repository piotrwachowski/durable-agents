"""Example 02 — Start all three workers for the sub-agent demo.

    # Terminal 1 — Temporal server
    temporal server start-dev

    # Terminal 2 — Start all three workers (blocks until Ctrl-C)
    uv run python examples/02_planner_subagents/worker.py

    # Terminal 3 — Submit a task
    uv run python examples/02_planner_subagents/client.py "Write and review a poem about autumn"

All three workflows (planner, writer, reviewer) are visible at http://localhost:8233.
The writer and reviewer appear as child workflows of the planner.
"""
from __future__ import annotations

import asyncio
import os

from durable_agents import create_durable_agent, tool

# Model for every agent below. Reads OPENAI_MODEL from the environment so the
# example works against OpenAI or a local server (Ollama/vLLM) without edits;
# the "openai:" provider prefix is added if missing. See docs/12-local-models.md.
_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
if not _MODEL.startswith("openai:"):
    _MODEL = f"openai:{_MODEL}"


@tool
async def draft_content(topic: str, style: str = "prose") -> str:
    """Draft original content on the given topic in the specified style."""
    return (
        f"[draft] {style.capitalize()} on '{topic}':\n"
        "The leaves turn gold and crimson, whispering farewells to summer. "
        "A quiet chill settles over the forest as the days grow shorter, "
        "each breath a small cloud vanishing into the cool air."
    )


@tool
async def review_content(content: str) -> str:
    """Review the provided content and return editorial feedback."""
    word_count = len(content.split())
    return (
        f"[review] Content reviewed ({word_count} words). "
        "Tone: evocative. Suggestion: consider adding a closing metaphor. "
        "Overall quality: good."
    )


writer_agent = create_durable_agent(
    model=_MODEL,
    tools=[draft_content],
    system_prompt=(
        "You are a creative writing assistant. "
        "Use the draft_content tool to produce well-crafted text on the given topic."
    ),
    task_queue="writer-agent",
    max_steps=5,
)

reviewer_agent = create_durable_agent(
    model=_MODEL,
    tools=[review_content],
    system_prompt=(
        "You are an editorial reviewer. "
        "Use the review_content tool to critique and improve submitted text."
    ),
    task_queue="reviewer-agent",
    max_steps=5,
)

planner_agent = create_durable_agent(
    model=_MODEL,
    tools=[],
    sub_agents={
        "writer": writer_agent,
        "reviewer": reviewer_agent,
    },
    system_prompt=(
        "You are a project planner. Break tasks into steps. "
        "Delegate writing steps to the 'writer' sub-agent and "
        "review/critique steps to the 'reviewer' sub-agent."
    ),
    task_queue="planner-agent",
    max_steps=10,
)


async def main() -> None:
    print("Starting workers on task queues:")
    print("  planner-agent  (orchestrator)")
    print("  writer-agent   (drafting)")
    print("  reviewer-agent (editorial review)")
    print("Temporal UI: http://localhost:8233")
    print("Press Ctrl-C to stop.\n")
    await asyncio.gather(
        planner_agent.run_worker(),
        writer_agent.run_worker(),
        reviewer_agent.run_worker(),
    )


if __name__ == "__main__":
    asyncio.run(main())
