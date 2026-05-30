# 4. Defining Agents

> **On this page:** [`create_durable_agent`](#create_durable_agent) · [Parameters](#parameters) · [The `Agent` handle](#the-agent-handle) · [Triggering a run with `DurableAgentClient`](#triggering-a-run-with-durableagentclient) · [Model identifiers](#model-identifiers)

## `create_durable_agent`

`create_durable_agent` is the worker-side factory. Calling it validates and
registers your tools and skills into the local `ToolRegistry`, stores the
agent's configuration, and returns an `Agent` handle.

```python
from durable_agents import create_durable_agent, tool

@tool
async def web_search(query: str) -> str:
    """Search the web for information about the given query."""
    ...

agent = create_durable_agent(
    model="openai:gpt-4o-mini",
    tools=[web_search],
    system_prompt="You are a helpful research assistant.",
    task_queue="research-agent",
    max_steps=10,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model` | `str` | *required* | Model identifier, e.g. `"openai:gpt-4o-mini"`. Must use a supported provider prefix. |
| `tools` | `list[Callable]` | `None` | Functions decorated with [`@tool`](05-tools.md). Passing an undecorated function raises `ValueError`. |
| `skills` | `list[type]` | `None` | Classes decorated with [`@skill`](07-skills.md). Each skill's tools are registered and its prompt fragment appended. |
| `sub_agents` | `dict[str, Agent]` | `None` | Mapping of sub-agent name → `Agent`. Enables [delegation](06-sub-agents.md). |
| `system_prompt` | `str` | `None` | System message prepended to every LLM call. |
| `task_queue` | `str` | `TEMPORAL_TASK_QUEUE` | Temporal task queue this agent serves. |
| `max_steps` | `int` | `20` | Maximum plan items before the workflow fails. |
| `context_limit` | `int` | `CONTEXT_LIMIT` (6000) | Estimated-token threshold that triggers context summarisation. |
| `temporal_host` | `str` | `TEMPORAL_HOST` | Temporal server address. |
| `temporal_namespace` | `str` | `TEMPORAL_NAMESPACE` | Temporal namespace. |

> Defaults shown in capitals come from [Configuration](10-configuration.md) and
> can be set via environment variables.

The factory raises `ValueError` if the `model` prefix is unsupported, a tool was
not decorated with `@tool`, or a skill is missing required attributes.

## The `Agent` handle

`create_durable_agent` returns an `Agent`, a small dataclass wrapping the
resolved `AgentConfig`. It has two async methods:

### `await agent.run_worker()`

Starts a Temporal worker that serves this agent's task queue. It registers
`AgentWorkflow` and all the framework activities, then **blocks** until the
process is interrupted. This is what you call in a `worker.py`.

```python
import asyncio
asyncio.run(agent.run_worker())
```

To run several agents (e.g. an orchestrator and its sub-agents) in one process,
gather their workers:

```python
await asyncio.gather(
    planner_agent.run_worker(),
    writer_agent.run_worker(),
    reviewer_agent.run_worker(),
)
```

### `await agent.run(task, ...)`

A same-process convenience that submits a task by delegating to
`DurableAgentClient`. Useful for scripts and tests where the worker and trigger
live together. Optional keyword arguments: `workflow_id`, `model_override`,
`max_steps`.

## Triggering a run with `DurableAgentClient`

In production the trigger is usually a **separate process** from the worker. Use
`DurableAgentClient`, which needs only the task-queue name:

```python
from durable_agents import DurableAgentClient

client = DurableAgentClient(
    task_queue="research-agent",
    # temporal_host=..., namespace=...  # optional overrides
)
result: str = await client.run(
    "What is quantum entanglement?",
    # workflow_id=...,        # optional, for deduplication / lookup
    # model_override=...,     # override the agent's default model for this run
    # max_steps=...,          # override the step ceiling for this run
)
```

The client has no knowledge of the agent's tools or prompt — it simply starts
the `AgentWorkflow` on the named task queue and awaits the result.

## Model identifiers

Models are identified with a `provider:model-name` string. The provider prefix
selects the backend; the framework currently supports:

| Prefix | Backend |
|---|---|
| `openai:` | OpenAI Chat Completions (e.g. `openai:gpt-4o-mini`) |

Additional providers are on the [roadmap](11-roadmap.md). Passing an unsupported
prefix raises `ValueError` at agent-creation time.

Next: [Tools](05-tools.md).
