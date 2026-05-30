# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-30

### Added
- Initial public release of the `durable-agents` framework.
- Agent-on-worker model with thin, dependency-free clients
  (`create_durable_agent`, `DurableAgentClient`).
- Durable plan-then-execute loop (`AgentWorkflow`): `create_plan` →
  per-item ReAct execution → `synthesize_result`, with context summarisation.
- `@tool` decorator with automatic JSON-schema generation and a worker-local
  `ToolRegistry`.
- Per-tool execution options (`@tool(timeout_seconds=..., max_retries=...)`)
  applied when a tool is dispatched. The values are resolved from the registry
  and carried on `ItemResult` so they are applied deterministically on workflow
  replay.
- Sub-agent delegation as Temporal child workflows, scoped to each agent's own
  configuration.
- `@skill` decorator for packaging reusable tools plus a prompt fragment.
- Built-in filesystem tools (`read_file`, `write_file`, `list_dir`,
  `search_files`).
- Three runnable examples and a chaptered documentation set.
- Initial test suite: unit tests for the `@tool` decorator, `ToolRegistry`,
  `create_durable_agent` validation, `dispatch_tool` error handling, and
  `create_plan` parsing/fallbacks, plus an end-to-end `AgentWorkflow` test
  against the Temporal test environment with stubbed activities.
- GitHub Actions CI (ruff, mypy, pytest on Python 3.11 and 3.12).
- `CONTRIBUTING.md` and this changelog.
