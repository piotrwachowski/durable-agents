# Examples

Runnable examples for the `durable_agents` framework, ordered from simplest to
most advanced. Each example lives in its own self-contained folder with a
`worker.py` (registers agents/tools and runs the Temporal workers) and a
`client.py` (submits a task to a task queue).

| # | Folder | Concept |
|---|--------|---------|
| 01 | [`01_research_agent/`](01_research_agent/) | A single agent with tools running a plan-then-execute loop. |
| 02 | [`02_planner_subagents/`](02_planner_subagents/) | A planner agent that delegates to `writer` and `reviewer` sub-agents (child workflows). |
| 03 | [`03_code_archaeologist/`](03_code_archaeologist/) | A four-agent pipeline that analyses, modernises, and documents legacy code on disk. |

## Prerequisites

- A running Temporal dev server: `temporal server start-dev`
- An `OPENAI_API_KEY` in your environment (see the project README).
- Dependencies installed: `uv sync`

## Running an example

Every example follows the same two-terminal pattern. Start the worker first,
then submit a task from a second terminal. Run all commands from the
repository root.

```bash
# Terminal 1 — start the worker (blocks until Ctrl-C)
uv run python examples/01_research_agent/worker.py

# Terminal 2 — submit a task
uv run python examples/01_research_agent/client.py "What is quantum entanglement?"
```

Swap in the folder name for examples 02 and 03. Each `worker.py` and
`client.py` docstring documents its exact invocation. All workflows are visible
in the Temporal Web UI at <http://localhost:8233>.
