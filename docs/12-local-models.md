# 12. Local models (Ollama & vLLM)

> **On this page:** [How local models work](#how-local-models-work) · [Tool-calling requirement](#tool-calling-requirement) · [Option A: Ollama](#option-a-ollama-with-a-web-ui) · [Option B: vLLM](#option-b-vllm) · [Choosing a model](#choosing-a-model) · [Per-agent / per-run model selection](#per-agent--per-run-model-selection) · [Troubleshooting](#troubleshooting)

`durable-agents` talks to the LLM through the **OpenAI chat-completions
protocol**. Any server that implements that protocol can drive the agent — you
just point the framework at it with one environment variable. Two popular local
servers are covered here:

- **[Ollama](https://ollama.com)** — the simplest way to run quantised models
  locally, with a one-command Docker setup and an optional web UI.
- **[vLLM](https://docs.vllm.ai)** — a high-throughput inference server, better
  suited to heavier load and full-precision / large models.

## How local models work

Set `OPENAI_BASE_URL` to the server's OpenAI-compatible endpoint and
`OPENAI_MODEL` to a model the server has loaded:

```bash
# .env
OPENAI_BASE_URL=http://localhost:11434/v1      # Ollama (vLLM uses :8000/v1)
OPENAI_MODEL=SpeakLeash/bielik-11b-v3.0-instruct:Q8_0
```

When `OPENAI_BASE_URL` is set, `OPENAI_API_KEY` becomes optional — local servers
ignore it, so the framework substitutes a placeholder rather than failing at
startup. See [Configuration](10-configuration.md#environment-variables).

Ollama model names usually carry a **quantization tag** after a colon
(e.g. `:Q4_K_M`), and these community models have **no `:latest` tag**, so the
tag is required — `ollama pull <name>` without one fails with
`pull model manifest: file does not exist`. The optional `openai:` provider
prefix is still recognised and stripped (`openai:org/model:Q4_K_M`), while the
quantization tag is preserved.

## Tool-calling requirement

The [plan-then-execute loop](03-core-concepts.md) relies on **OpenAI
function/tool calling**: the planner forces a `write_plan` function and passes
your tools as JSON schemas. A local model must therefore support tool calling for
the agent to work reliably.

- On Ollama, prefer models that publish a **`tools`** capability tag.
- On vLLM, start the server with `--enable-auto-tool-choice` and a matching
  `--tool-call-parser` (see below).

Small or older models may produce malformed tool calls. The framework turns those
into recoverable observations, but a tool-capable model gives far better results.

## Option A: Ollama with a web UI

The repository's [`docker-compose.yml`](../docker-compose.yml) defines an
optional `local-llm` profile with three services:

| Service | Purpose | URL |
|---|---|---|
| `ollama` | OpenAI-compatible model server | `http://localhost:11434/v1` |
| `ollama-init` | One-shot job that pulls the default models | — |
| `open-webui` | Web chat UI for browsing/testing models | `http://localhost:3000` |

Start them (in addition to whatever is already running):

```bash
docker compose --profile local-llm up -d
```

> **Note:** these services live under a `local-llm` Compose *profile*, so a plain
> `docker compose up -d` **skips them** — you must pass `--profile local-llm` to
> start (or stop) them. This keeps the GPU-bound model services opt-in.

The `ollama-init` job waits for the server, then pulls the default models. Watch
its progress with:

```bash
docker compose logs -f ollama-init
```

Then configure the framework:

```bash
# .env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=SpeakLeash/bielik-11b-v3.0-instruct:Q8_0
```

Pull additional models at any time:

```bash
docker compose exec ollama ollama pull <model-tag>
docker compose exec ollama ollama list      # see what's available
```

### GPU vs CPU

The `ollama` service requests an NVIDIA GPU via its `deploy` block, which needs
the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
installed on the host. To run CPU-only (much slower), delete the `deploy` block
from the `ollama` service.

## Option B: vLLM

vLLM serves a single model over an OpenAI-compatible API and is a good fit for
higher throughput or full-precision weights. The official Docker image is the
most portable way to run it on a GPU host:

```bash
docker run --rm --gpus all \
  -p 8000:8000 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  vllm/vllm-openai:latest \
  --model speakleash/Bielik-11B-v3.0-Instruct \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90
```

Notes:

- `--enable-auto-tool-choice` + `--tool-call-parser` are **required** for the
  agent's tool calling. The correct parser depends on the model's chat template
  (`hermes`, `llama3_json`, `mistral`, …); check the model card and vLLM's
  [tool-calling docs](https://docs.vllm.ai/en/latest/features/tool_calling.html).
- Full-precision weights are large. If a model does not fit in available VRAM,
  use a quantised checkpoint (AWQ/GPTQ) and add `--quantization awq` (or `gptq`),
  and/or lower `--max-model-len` and `--gpu-memory-utilization`.
- vLLM targets Linux + NVIDIA. On Windows, run it inside WSL2 or via the Docker
  image above.

Point the framework at it:

```bash
# .env
OPENAI_BASE_URL=http://localhost:8000/v1
OPENAI_MODEL=speakleash/Bielik-11B-v3.0-Instruct
```

## Choosing a model

For Polish-language work (e.g. document generation) and legacy-modernisation
agents such as **COBOL → documentation** or **Java explanation**, two Polish
model families are good starting points. Both are open and available in
quantised form.

| Model | Ollama tag | Tool calling | Notes |
|---|---|---|---|
| **Bielik 11B v3.0 Instruct** (SpeakLeash) | `SpeakLeash/bielik-11b-v3.0-instruct:Q8_0` | ✅ `tools` tag | Strong Polish + reliable tool calling — recommended default driver. Lighter quants available: `:Q4_K_M`, `:Q5_K_M`, `:Q6_K`. |
| Bielik Minitron 7B v3.0 (SpeakLeash) | `SpeakLeash/bielik-minitron-7B-v3.0-instruct` | ✅ `tools` tag | Lighter / faster fallback. |
| **PLLuM 12B** (Ministry of Digital Affairs) | `bbaranow/pllum-12B-q4_k_m` | ⚠️ limited | Government-backed Polish model; good for Polish prose, weaker at tool calling. |

Practical guidance, hardware-neutral:

- Quantised 7B–12B models (Q4–Q8) need on the order of single-digit to low-teens
  GB of memory and run comfortably on a modern consumer GPU; full-precision or
  larger (e.g. 70B / MoE) models need substantially more or must be quantised.
- For the agent's tool-driven loop, **prefer a tool-capable model** (Bielik
  v3.0) as the driver. A non-tool model can still be used for pure text steps
  (e.g. summarising extracted code) via per-agent model selection below.
- Model availability and tags change over time — verify the current tag on
  [ollama.com](https://ollama.com/search?q=bielik) before pulling.

## Per-agent / per-run model selection

You are not limited to a single model. You can mix a tool-capable driver with a
different model for specific agents or runs:

```python
agent = create_durable_agent(
    model="SpeakLeash/bielik-11b-v3.0-instruct:Q8_0",  # tool-capable driver
    # ...
)
```

```python
await client.run(
    "Document this COBOL program.",
    model_override="bbaranow/pllum-12B-q4_k_m",   # different model for one run
)
```

See [Configuration → per-agent / per-run overrides](10-configuration.md#per-agent-overrides).

## Troubleshooting

- **Startup `KeyError: 'OPENAI_API_KEY'`** — set `OPENAI_BASE_URL`; the key
  becomes optional only when a base URL is present.
- **Connection refused** — confirm the server is up (`docker compose ps`) and the
  port matches: Ollama uses `11434`, vLLM uses `8000`. From inside another
  container use the service name (`http://ollama:11434/v1`), not `localhost`.
- **`model not found`** — pull it first (`ollama pull <tag>` / `ollama list`), and
  make sure `OPENAI_MODEL` exactly matches the served tag.
- **`pull model manifest: file does not exist`** — the tag has no `:latest`;
  include an explicit quantization tag, e.g. `...:Q4_K_M`.
- **Plans never form / malformed tool calls** — the model likely lacks reliable
  tool support. Switch to a tool-capable model, or for vLLM verify
  `--enable-auto-tool-choice` and the correct `--tool-call-parser`.

Next: [Roadmap](11-roadmap.md).
