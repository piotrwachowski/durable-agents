"""Shared pytest configuration for the durable-agents test suite.

A dummy ``OPENAI_API_KEY`` is set *before* any package import so that
``durable_agents.config`` (which reads the key at import time) and the
module-level ``AsyncOpenAI`` clients can be constructed. No network calls are
made during the unit tests — the OpenAI client is either unused or monkeypatched.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")
