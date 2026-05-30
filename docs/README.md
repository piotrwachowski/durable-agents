# Documentation

Welcome to the `durable-agents` documentation. These chapters take you from a
high-level introduction through the core concepts, the public API, and the
internal architecture.

## Table of contents

1. [Introduction](01-introduction.md) — what `durable-agents` is, the case for durable execution, and the design philosophy.
2. [Getting Started](02-getting-started.md) — install dependencies, configure your environment, and run your first agent.
3. [Core Concepts](03-core-concepts.md) — the agent-on-worker model, the plan-then-execute loop, and the determinism rules.
4. [Defining Agents](04-defining-agents.md) — the `create_durable_agent` factory and every parameter it accepts.
5. [Tools](05-tools.md) — authoring tools with `@tool`, the tool registry, and the built-in filesystem tools.
6. [Sub-Agents](06-sub-agents.md) — delegating work to other agents that run as child workflows.
7. [Skills](07-skills.md) — packaging reusable capability with the `@skill` decorator.
8. [Architecture](08-architecture.md) — how agents map onto Temporal workflows and activities, and the data models.
9. [Examples](09-examples.md) — a guided tour of the bundled examples.
10. [Configuration](10-configuration.md) — the full environment-variable reference.
11. [Roadmap](11-roadmap.md) — implemented phases and what is planned next.

## How to read these docs

- **New to the project?** Read chapters 1–3 in order, then run the example in chapter 2.
- **Building an agent?** Chapters 4–7 are the practical API reference.
- **Curious how it works?** Chapter 8 explains the Temporal mapping and determinism guarantees.

> Throughout the docs, "the framework" refers to the `durable_agents` package in
> [`src/durable_agents/`](../src/durable_agents/).
