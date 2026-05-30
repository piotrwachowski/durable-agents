from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Try the project root (.env sits next to pyproject.toml), then fall back to CWD.
load_dotenv(Path(__file__).parent.parent.parent / ".env")
load_dotenv()

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ── Temporal ──────────────────────────────────────────────────────────────────
TEMPORAL_HOST: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
TEMPORAL_NAMESPACE: str = os.getenv("TEMPORAL_NAMESPACE", "default")
TEMPORAL_TASK_QUEUE: str = os.getenv("TEMPORAL_TASK_QUEUE", "durable-agents")

# ── Agent behaviour ───────────────────────────────────────────────────────────
CONTEXT_LIMIT: int = int(os.getenv("CONTEXT_LIMIT", "6000"))
MAX_STEPS: int = int(os.getenv("DURABLE_AGENT_MAX_STEPS", "20"))
