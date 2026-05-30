# 8. Architecture

> **On this page:** [The mapping](#the-mapping) · [`AgentWorkflow`](#agentworkflow) · [Activities](#activities) · [Data models](#data-models) · [Event history](#event-history) · [Module layout](#module-layout)

This chapter is the reference for how the framework is put together. For the
intuition behind it, read [Core Concepts](03-core-concepts.md) first.

## The mapping

`durable-agents` projects the agent loop onto Temporal primitives:

| Agent concept | Temporal primitive | Where |
|---|---|---|
| An agent run | Workflow | `AgentWorkflow` |
| Planning | Activity | `create_plan` |
| Working a plan item | Activity | `execute_plan_item` |
| A tool call | Activity | `dispatch_tool` |
| Preparing a delegation | Activity | `prepare_delegation` |
| Final answer | Activity | `synthesize_result` |
| Context compaction | Activity | `summarise_context` |
| A sub-agent | Child workflow | `AgentWorkflow.run` on another task queue |
| The agent's memory | Event history | persisted by Temporal |

## `AgentWorkflow`

`AgentWorkflow` (`workflows/agent_workflow.py`) is the deterministic heart of the
framework. It implements the three-phase loop:

1. **Plan** — calls `create_plan` to produce a `Plan` of `TodoItem`s.
2. **Execute** — a `while` loop over pending items:
   - `delegate` items start a **child workflow** on the sub-agent's task queue
     (after `prepare_delegation` crafts the child's task).
   - other items run a bounded **inner ReAct loop**: `execute_plan_item` decides
     whether to call a tool; if so, `dispatch_tool` runs it and the call + result
     are threaded back into the item's working history. The inner loop is capped
     at `_MAX_TOOL_ITERATIONS` (8) per item.
   - before working an item, if the estimated history size exceeds
     `context_limit`, `summarise_context` compacts it.
   - a `max_steps` guard fails the run if it takes too many steps.
3. **Synthesize** — calls `synthesize_result` to write the final answer.

It also exposes a `get_todo_list` **query**, so you can inspect the live plan of
a running agent from the Temporal UI or a client.

All activity imports are wrapped in `workflow.unsafe.imports_passed_through()` so
the workflow sandbox never executes their module-level side effects (such as
constructing the `AsyncOpenAI` client) during replay — a hard
[determinism rule](03-core-concepts.md#determinism-rules).

## Activities

Every side-effecting step is an activity. They are registered automatically by
`Agent.run_worker()`.

| Activity | Module | Responsibility |
|---|---|---|
| `create_plan` | `activities/planner.py` | LLM call → structured `Plan`; resolves `sub_task_queue` for delegate items from the agent's config. |
| `execute_plan_item` | `activities/planner.py` | LLM call for one item; returns an `ItemResult`, optionally requesting a tool. |
| `prepare_delegation` | `activities/planner.py` | Distil parent history into a self-contained task string for a child agent. |
| `synthesize_result` | `activities/planner.py` | LLM call → final answer from the completed plan + history. |
| `dispatch_tool` | `activities/dispatcher.py` | Look up the tool in the registry and invoke it; catches errors and returns them as observations. |
| `summarise_context` | `activities/context.py` | Compact the running history when it grows past `context_limit`. |

## Data models

The dataclasses in `models.py` are the wire and in-memory contract:

| Type | Key fields | Purpose |
|---|---|---|
| `AgentInput` | `task`, `model_override`, `max_steps` | What a client sends to start a run. |
| `AgentConfig` | `model`, `task_queue`, `system_prompt`, `max_steps`, `context_limit`, `temporal_host`, `temporal_namespace`, `sub_agent_task_queues`, `tool_names` | The resolved agent definition stored on the worker. |
| `ToolEntry` | `name`, `callable`, `description`, `parameters`, `timeout_seconds`, `max_retries` | A registered tool and its generated JSON schema. |
| `TodoItem` | `id`, `title`, `description`, `type` (`tool_call`/`delegate`/`wait`), `status`, `sub_agent_name`, `sub_task_queue` | One step in a plan. |
| `Plan` | `items` | The ordered list of `TodoItem`s. |
| `ItemResult` | `item_id`, `output`, `tool_name`, `tool_args`, `tool_call_id` | The outcome of working one item, including any requested tool call. |

Note that `AgentConfig` carries only `tool_names` and `sub_agent_task_queues` —
**not** the tool callables. The callables live in the worker-local registry, which
is why clients never need them (see [Core Concepts](03-core-concepts.md)).

## Event history

Everything above is recorded in Temporal's append-only event history: the plan,
every activity input and output, each child-workflow result. That history *is* the
agent's memory of the run. If a worker dies, Temporal replays the history on
another worker and resumes from the exact point of failure. You can open any run
in the Web UI and read its complete reasoning trace.

## Module layout

```text
src/durable_agents/
├── __init__.py          # public API: create_durable_agent, DurableAgentClient, tool, skill
├── config.py            # env-var configuration
├── models.py            # dataclasses (AgentInput, AgentConfig, TodoItem, Plan, ...)
├── activities/
│   ├── planner.py       # create_plan, execute_plan_item, prepare_delegation, synthesize_result
│   ├── dispatcher.py    # dispatch_tool
│   └── context.py       # summarise_context
├── harness/
│   ├── agent.py         # create_durable_agent + Agent handle
│   ├── client.py        # DurableAgentClient
│   ├── registry.py      # ToolRegistry
│   ├── skill.py         # @skill decorator
│   └── state.py         # per-task-queue AgentConfig storage
├── tools/
│   ├── decorators.py    # @tool decorator + schema generation
│   └── filesystem.py    # built-in read/write/list/search tools
└── workflows/
    └── agent_workflow.py  # AgentWorkflow
```

Next: [Examples](09-examples.md).
