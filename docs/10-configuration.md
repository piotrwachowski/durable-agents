# 10. Configuration

> **On this page:** [How configuration is loaded](#how-configuration-is-loaded) · [Environment variables](#environment-variables) · [Per-agent overrides](#per-agent-overrides) · [Per-run overrides](#per-run-overrides) · [Precedence](#precedence)

## How configuration is loaded

Configuration lives in environment variables, read once at import time by
`config.py`. A `.env` file is loaded automatically: first from the project root
(next to `pyproject.toml`), then from the current working directory. Copy the
template to get started:

```bash
cp .env.example .env
```

`OPENAI_API_KEY` is **required** — it is read with `os.environ[...]`, so a
missing key raises `KeyError` at startup. Every other value has a default.

## Environment variables

| Variable | Default | Used for |
|---|---|---|
| `OPENAI_API_KEY` | *required* | Authenticating with OpenAI. No default; startup fails without it — **unless `OPENAI_BASE_URL` is set**, in which case it defaults to a placeholder (`local`). |
| `OPENAI_BASE_URL` | *(empty)* | Base URL of an OpenAI-compatible server (e.g. `http://localhost:11434/v1` for Ollama, or a vLLM endpoint). Empty means the OpenAI cloud API. See [Local models](12-local-models.md). |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default model name (the part after the `openai:` prefix). |
| `LLM_MAX_TOKENS` | `4096` | Max tokens per LLM completion. |
| `TEMPORAL_HOST` | `localhost:7233` | Temporal server gRPC address. |
| `TEMPORAL_NAMESPACE` | `default` | Temporal namespace. |
| `TEMPORAL_TASK_QUEUE` | `durable-agents` | Default task queue when an agent does not set one. |
| `CONTEXT_LIMIT` | `6000` | Estimated-token threshold that triggers context summarisation. |
| `DURABLE_AGENT_MAX_STEPS` | `20` | Default maximum plan steps per run. |

These provide the *defaults*. Most can be overridden per agent or per run, as
described below.

## Per-agent overrides

[`create_durable_agent`](04-defining-agents.md#parameters) accepts arguments that
override the environment defaults for that specific agent:

```python
agent = create_durable_agent(
    model="openai:gpt-4o-mini",   # overrides OPENAI_MODEL (with provider prefix)
    task_queue="my-agent",        # overrides TEMPORAL_TASK_QUEUE
    max_steps=10,                 # overrides DURABLE_AGENT_MAX_STEPS
    context_limit=8000,           # overrides CONTEXT_LIMIT
    temporal_host="temporal:7233",# overrides TEMPORAL_HOST
    temporal_namespace="prod",    # overrides TEMPORAL_NAMESPACE
)
```

These values are stored in the agent's [`AgentConfig`](08-architecture.md#data-models)
on the worker.

## Per-run overrides

A few settings can be overridden per task submission via
[`DurableAgentClient.run`](04-defining-agents.md#triggering-a-run-with-durableagentclient)
(or `Agent.run`):

```python
await client.run(
    "Summarise this report.",
    model_override="openai:gpt-4o",  # use a stronger model just for this run
    max_steps=30,                    # raise the step ceiling for this run
)
```

`model_override` and `max_steps` travel inside the
[`AgentInput`](08-architecture.md#data-models) message.

## Precedence

From lowest to highest priority:

```text
environment / .env defaults  →  create_durable_agent(...) per-agent  →  client.run(...) per-run
```

In other words, a per-run override wins over the agent's configuration, which in
turn wins over the environment defaults.

Next: [Roadmap](11-roadmap.md).
