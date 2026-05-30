# Contributing to durable-agents

Thanks for your interest in contributing! This project is in **alpha**, and
contributions — bug reports, ideas, docs, and code — are all welcome.

## Getting set up

```bash
uv sync --group dev
cp .env.example .env   # set OPENAI_API_KEY for running examples
```

## Development workflow

Run the full check suite locally before opening a pull request — these are the
same checks CI runs:

```bash
uv run ruff check .     # lint
uv run mypy src         # type-check
uv run pytest -q        # tests
```

To auto-fix lint and format issues:

```bash
uv run ruff check --fix .
uv run ruff format .
```

## Hard rules (please read)

This framework runs on [Temporal](https://temporal.io), so **workflow code must
stay deterministic**. When changing anything under
`src/durable_agents/workflows/`:

- No I/O, `random`, or `datetime.now()` in workflow code — use `workflow.now()`.
- All side effects (LLM calls, tool calls, DB access) belong in **activities**.
- Keep activity imports wrapped in `workflow.unsafe.imports_passed_through()`.
- Treat malformed model output as a recoverable **observation**, not an
  exception — never crash the loop on bad LLM output.

See [docs/03-core-concepts.md](docs/03-core-concepts.md) and
[docs/08-architecture.md](docs/08-architecture.md) for the full rationale.

## Pull requests

- Keep changes focused; one logical change per PR.
- Add or update tests for any behaviour change.
- Update the relevant chapter in `docs/` if you change public behaviour.
- Add an entry to [CHANGELOG.md](CHANGELOG.md) under "Unreleased".

## Reporting bugs

Open an issue with a minimal reproduction: the agent/tool definition, the task,
and what you expected vs. what happened. A link to the failing workflow in the
Temporal Web UI (or its event history) is enormously helpful.
