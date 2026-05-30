# 2. Getting Started

> **On this page:** [Prerequisites](#prerequisites) · [Install](#install) · [Configure](#configure) · [Start Temporal](#start-temporal) · [Run your first agent](#run-your-first-agent) · [Verify in the Web UI](#verify-in-the-web-ui) · [Troubleshooting](#troubleshooting)

## Prerequisites

- **Python 3.11+**
- An **OpenAI API key**
- [**uv**](https://docs.astral.sh/uv/) (recommended) or pip
- **Docker** to run the bundled Temporal server — or the
  [Temporal CLI](https://docs.temporal.io/cli) if you prefer `temporal server start-dev`

## Install

```bash
uv sync
```

This creates a virtual environment and installs the runtime dependencies:
`temporalio`, `openai`, and `python-dotenv`.

## Configure

The framework reads configuration from environment variables, with a `.env` file
loaded automatically at startup.

```bash
cp .env.example .env
```

Edit `.env` and set at least your API key:

```ini
OPENAI_API_KEY=sk-...
```

All other settings have sensible defaults — see [Configuration](10-configuration.md)
for the full list.

## Start Temporal

The repository ships a `docker-compose.yml` that starts a Postgres-backed
Temporal server plus the Web UI:

```bash
docker compose up -d
```

| Service | Address |
|---|---|
| Temporal gRPC endpoint | `localhost:7233` |
| Temporal Web UI | <http://localhost:8233> |

Prefer not to use Docker? Install the Temporal CLI and run:

```bash
temporal server start-dev
```

## Run your first agent

Every example is a self-contained folder with a `worker.py` (defines and serves
the agent) and a `client.py` (submits a task). Start the worker first:

```bash
# Terminal 1 — worker (blocks until Ctrl-C)
uv run python examples/01_research_agent/worker.py
```

Then, in a second terminal, submit a task:

```bash
# Terminal 2 — client
uv run python examples/01_research_agent/client.py "What is quantum entanglement?"
```

The client prints the final answer and exits. The worker keeps running, ready
for the next task.

## Verify in the Web UI

Open <http://localhost:8233> and find the `AgentWorkflow` execution. Click into
it to see the full event history: the `create_plan` activity, each
`execute_plan_item` / `dispatch_tool` call, and the final `synthesize_result`.
This is your agent's durable memory, made visible.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `KeyError: 'OPENAI_API_KEY'` on startup | No `.env` / key not set | `cp .env.example .env` and set the key |
| Client hangs forever | Worker not running, or wrong task queue | Start the matching `worker.py` first |
| `Connection refused` to `localhost:7233` | Temporal not running | `docker compose up -d` or `temporal server start-dev` |
| Worker logs a code change but behaviour is unchanged | Worker caches the old code | Stop (Ctrl-C) and restart the worker |

Next: [Core Concepts](03-core-concepts.md).
