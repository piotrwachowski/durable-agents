# 1. Introduction

> **On this page:** [What it is](#what-it-is) · [The problem with in-memory agents](#the-problem-with-in-memory-agents) · [Why Temporal](#why-temporal) · [Design philosophy](#design-philosophy) · [What's next](#whats-next)

## What it is

`durable-agents` is a Python framework for building **durable, multi-agent
systems**. It offers the developer experience popularised by
[DeepAgents](https://github.com/langchain-ai/deepagents) — agents, tools,
skills, sub-agent delegation, and a plan-then-execute loop — but it replaces the
in-process state machine with [Temporal](https://temporal.io) durable execution.

In practice that means an agent is not a transient object living in one Python
process. It is a **Temporal workflow** whose entire history — every plan, tool
call, observation, and delegation — is persisted as it happens. The framework's
job is to make that durability invisible: you write ordinary `async` Python and
get crash-proof agents.

## The problem with in-memory agents

Most agent frameworks keep the agent's state (the message list, the current
plan, intermediate results) in memory. That works in a notebook, but it is
fragile in production:

- A process crash, deploy, or OOM kill **loses the entire run**.
- A transient `500` or rate-limit from the model provider **aborts the agent**
  unless you hand-roll retry logic.
- A single malformed tool call can throw an exception that **unwinds the whole
  loop**.
- Long-running work (waiting on a human, a slow job, or a scheduled step) means
  **holding a process open** and hoping nothing restarts.

These are exactly the problems durable execution engines were built to solve.

## Why Temporal

[Temporal](https://temporal.io) runs your code as **deterministic workflows**
backed by an append-only **event history**. Side-effecting work runs in
**activities**, which are retried automatically on failure. If a worker dies,
Temporal replays the workflow's history on another worker and continues from the
exact point of failure — no state is lost.

`durable-agents` maps the agent loop onto this model:

| Agent concept | Temporal primitive |
|---|---|
| The agent run | A **workflow** (`AgentWorkflow`) |
| An LLM call (plan, execute, synthesize) | An **activity** |
| A tool invocation | An **activity** (`dispatch_tool`) |
| A sub-agent | A **child workflow** |
| The agent's memory of the run | The workflow's **event history** |

Because activities are retried and workflows are replayable, the agent inherits
durability for free. See [Architecture](08-architecture.md) for the full mapping.

## Design philosophy

A few principles shape the framework:

1. **Durable by construction, not by configuration.** You should not have to
   think about checkpoints or retries for the common case — the execution model
   provides them.
2. **The worker *is* the agent.** Tools, prompts, and skills live only on the
   worker process. Clients are thin and dependency-free; they only know a
   task-queue name. See [Core Concepts](03-core-concepts.md).
3. **Bad model output is data, not an exception.** A truncated tool call or a
   reference to a non-existent file becomes an *observation* the model can
   correct on its next step, rather than a crash.
4. **Two retry layers, two purposes.** Temporal activity retries handle
   *transient infrastructure* faults (re-running identical work). The
   plan-then-execute loop handles *semantic* faults (so the model takes a
   different, corrective action). Neither is a substitute for the other.
5. **Small surface, easy to extend.** The public API is a handful of
   symbols — `create_durable_agent`, `DurableAgentClient`, `tool`, `skill`.

## What's next

Continue to [Getting Started](02-getting-started.md) to install the framework and
run your first agent, or jump to [Core Concepts](03-core-concepts.md) for the
mental model.
