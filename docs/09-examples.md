# 9. Examples

> **On this page:** [How examples are structured](#how-examples-are-structured) · [Example 01 — Research Agent](#example-01--research-agent) · [Example 02 — Planner + Sub-Agents](#example-02--planner--sub-agents) · [Example 03 — Code Archaeologist](#example-03--code-archaeologist)

The `examples/` folder contains three runnable examples, ordered simplest to most
advanced. Each is a self-contained folder.

## How examples are structured

Every example follows the same shape:

- **`worker.py`** — defines the agent(s), registers tools, and runs the Temporal
  worker(s). It blocks until interrupted.
- **`client.py`** — submits a task to a task queue and prints the result.

The two-terminal pattern is always the same (run from the project root):

```bash
# Terminal 1 — worker
uv run python examples/<folder>/worker.py

# Terminal 2 — client
uv run python examples/<folder>/client.py "your task here"
```

All runs are visible in the Temporal Web UI at <http://localhost:8233>.

| # | Folder | Concept |
|---|---|---|
| 01 | [`01_research_agent/`](../examples/01_research_agent/) | A single agent with tools running the plan-then-execute loop. |
| 02 | [`02_planner_subagents/`](../examples/02_planner_subagents/) | A planner delegating to `writer` and `reviewer` sub-agents. |
| 03 | [`03_code_archaeologist/`](../examples/03_code_archaeologist/) | A four-agent pipeline that analyses, modernises, and documents legacy code. |

## Example 01 — Research Agent

**Folder:** `examples/01_research_agent/` · **Concept:** a single agent with tools.

A minimal research assistant. It registers two tools (`web_search` and
`summarise`) and runs the standard plan-then-execute loop on a single task queue
(`research-agent`). This is the best place to start — it shows the full agent
lifecycle with no delegation.

```bash
uv run python examples/01_research_agent/worker.py
uv run python examples/01_research_agent/client.py "What is quantum entanglement?"
```

What to look for in the Web UI: a `create_plan` activity, one or more
`execute_plan_item` → `dispatch_tool` pairs, then `synthesize_result`.

Concepts: [Tools](05-tools.md), [Core Concepts](03-core-concepts.md).

## Example 02 — Planner + Sub-Agents

**Folder:** `examples/02_planner_subagents/` · **Concept:** delegation to
sub-agents.

A `planner` agent (task queue `planner-agent`) delegates to two specialists — a
`writer` (`writer-agent`) and a `reviewer` (`reviewer-agent`). The worker runs
all three agents together with `asyncio.gather`; you trigger only the planner,
which orchestrates the rest via child workflows.

```bash
uv run python examples/02_planner_subagents/worker.py
uv run python examples/02_planner_subagents/client.py "Write and review a short post about durable execution."
```

What to look for: the parent `AgentWorkflow` spawns child `AgentWorkflow`
executions on the `writer-agent` and `reviewer-agent` task queues, each with its
own isolated history.

Concepts: [Sub-Agents](06-sub-agents.md).

## Example 03 — Code Archaeologist

**Folder:** `examples/03_code_archaeologist/` · **Concept:** a multi-agent
pipeline over real files.

The most complete example: a four-agent pipeline that inspects legacy code on
disk and produces a modernisation plan and documentation.

- **orchestrator** — plans the work and delegates each phase.
- **archaeologist** — explores and explains the legacy code using the
  [filesystem tools](05-tools.md#built-in-filesystem-tools).
- **modernizer** — proposes concrete modernisation changes.
- **documenter** — writes up the findings.

Sample legacy code to analyse lives in `examples/03_code_archaeologist/legacy/`.

```bash
uv run python examples/03_code_archaeologist/worker.py
uv run python examples/03_code_archaeologist/client.py
```

What to look for: a chain of delegations where each sub-agent receives a crafted,
self-contained task (via `prepare_delegation`) carrying forward the previous
stage's findings, while keeping an isolated context.

Concepts: [Sub-Agents](06-sub-agents.md), [Tools](05-tools.md),
[Architecture](08-architecture.md).

Next: [Configuration](10-configuration.md).
