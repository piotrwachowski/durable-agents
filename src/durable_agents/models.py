from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolEntry:
    name: str
    callable: Any  # the original async function
    description: str
    parameters: dict[str, Any]  # JSON schema for the function parameters
    timeout_seconds: int | None = None
    max_retries: int | None = None


@dataclass
class AgentInput:
    task: str
    model_override: str | None = None
    max_steps: int = 20


@dataclass
class AgentConfig:
    model: str  # e.g. "openai:gpt-4o-mini"
    task_queue: str
    system_prompt: str | None = None
    max_steps: int = 20
    context_limit: int = 6000
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    sub_agent_task_queues: dict[str, str] = field(default_factory=dict)
    tool_names: list[str] = field(default_factory=list)


@dataclass
class RuntimeConfig:
    """Per-run agent settings resolved on the worker and returned to the workflow.

    The workflow runs in Temporal's sandbox where the process-local agent
    registry is not visible, so it cannot read AgentConfig directly. This
    lightweight value is produced by the ``load_runtime_config`` activity (which
    runs as ordinary host code) and carried in event history.
    """

    model: str
    system_prompt: str | None = None
    context_limit: int = 6000


@dataclass
class TodoItem:
    id: int
    title: str
    description: str
    type: Literal["tool_call", "delegate", "wait"]
    status: Literal["pending", "in_progress", "done", "failed"] = "pending"
    sub_agent_name: str | None = None
    sub_task_queue: str | None = None  # resolved by create_plan activity


@dataclass
class Plan:
    items: list[TodoItem] = field(default_factory=list)


@dataclass
class ItemResult:
    item_id: int
    output: str
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_call_id: str | None = None  # OpenAI tool_call id, for threading tool results
    # Per-tool execution options resolved from the registry at execute time and
    # carried in event history so the workflow can apply them deterministically.
    tool_timeout_seconds: int | None = None
    tool_max_retries: int | None = None
