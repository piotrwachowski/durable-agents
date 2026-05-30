# 11. Roadmap

> **On this page:** [Where we are](#where-we-are) · [What's next](#whats-next) · [A note on stability](#a-note-on-stability)

This chapter describes the direction of the project. It is a statement of intent,
not a commitment — priorities may shift, and dates are deliberately omitted.

## Where we are

The framework today provides a complete, durable, multi-agent foundation:

- ✅ **Agent-on-worker model** — agents defined and served on Temporal workers;
  thin, dependency-free clients.
- ✅ **Plan-then-execute loop** — durable three-phase loop
  (`create_plan` → execute → `synthesize_result`) with a per-item ReAct inner
  loop and context summarisation.
- ✅ **Tools** — the [`@tool`](05-tools.md) decorator with automatic JSON-schema
  generation and a worker-local registry.
- ✅ **Sub-agents** — [delegation](06-sub-agents.md) to specialist agents as
  isolated child workflows.
- ✅ **Skills** — the [`@skill`](07-skills.md) decorator for packaging reusable
  tools + prompt fragments.
- ✅ **Built-in filesystem tools** — `read_file`, `write_file`, `list_dir`,
  `search_files`.

## What's next

The following capabilities are planned. They are grouped by theme rather than
strict sequence.

### More built-in tools

Expand the standard library of tools beyond the filesystem:

- A **shell / command** tool for running processes durably.
- An **MCP client** so agents can consume [Model Context Protocol](https://modelcontextprotocol.io)
  servers as tools.

### Human-in-the-loop

Let an agent **pause and wait for a human** — for approval, clarification, or
input — and resume durably when the response arrives. This maps naturally onto
**Temporal signals**: a `wait` plan item parks the workflow until a signal
delivers the human's decision, with no process held open in between.

### Persistent memory

Give agents memory that **outlives a single run** — recalling facts, preferences,
and prior results across invocations. The intended backing stores are durable
services such as **Postgres** or **Redis**, surfaced to the agent as retrieval
tools.

### More model providers

Broaden beyond the current `openai:` backend. The `provider:model` identifier
scheme is designed so that additional providers can be added behind the same
`create_durable_agent(model=...)` interface.

### Observability & streaming

Make agent behaviour easy to inspect and operate in production:

- **Tracing** via OpenTelemetry and integrations such as LangSmith.
- **Streaming** of intermediate output to clients.
- Exploration of **Temporal Nexus** for cross-namespace / cross-team agent
  composition.

## A note on stability

The framework is **alpha**. The public surface is intentionally small —
`create_durable_agent`, `DurableAgentClient`, `tool`, `skill` — and we aim to keep
it stable, but APIs may change as the roadmap above lands. Pin a version if you
depend on the framework, and watch the changelog for breaking changes.

Have a use case or a feature request? See [Contributing](../README.md#contributing)
in the README.
