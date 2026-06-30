from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from durable_agents.config import (
    CONTEXT_LIMIT,
    TEMPORAL_HOST,
    TEMPORAL_NAMESPACE,
    TEMPORAL_TASK_QUEUE,
)
from durable_agents.harness.state import set_agent_config
from durable_agents.models import AgentConfig

_SUPPORTED_PREFIXES = ("openai:",)


@dataclass
class Agent:
    """Handle returned by create_durable_agent.

    Call await agent.run_worker() on the worker side to start serving tasks,
    or await agent.run(task) as a same-process convenience to submit work.
    """

    config: AgentConfig

    async def run_worker(self) -> None:
        """Start a Temporal worker that serves this agent task queue.

        Registers AgentWorkflow and all Phase-1 activities, then blocks
        until the process is interrupted.
        """
        import asyncio

        from temporalio.client import Client
        from temporalio.worker import Worker

        from durable_agents.activities.context import summarise_context
        from durable_agents.activities.dispatcher import dispatch_tool
        from durable_agents.activities.planner import (
            create_plan,
            execute_plan_item,
            load_runtime_config,
            prepare_delegation,
            synthesize_result,
        )
        from durable_agents.workflows.agent_workflow import AgentWorkflow

        client = await Client.connect(
            self.config.temporal_host, namespace=self.config.temporal_namespace
        )
        async with Worker(
            client,
            task_queue=self.config.task_queue,
            workflows=[AgentWorkflow],
            activities=[
                create_plan,
                execute_plan_item,
                prepare_delegation,
                synthesize_result,
                dispatch_tool,
                summarise_context,
                load_runtime_config,
            ],
        ):
            await asyncio.get_running_loop().create_future()

    async def run(
        self,
        task: str,
        *,
        workflow_id: str | None = None,
        model_override: str | None = None,
        max_steps: int | None = None,
    ) -> str:
        """Convenience wrapper that delegates to DurableAgentClient."""
        from durable_agents.harness.client import DurableAgentClient

        return await DurableAgentClient(
            task_queue=self.config.task_queue,
            temporal_host=self.config.temporal_host,
            namespace=self.config.temporal_namespace,
        ).run(
            task,
            workflow_id=workflow_id,
            model_override=model_override,
            # Fall back to the configured max_steps when the caller doesn't override.
            max_steps=max_steps if max_steps is not None else self.config.max_steps,
        )


def create_durable_agent(
    model: str,
    tools: list[Callable[..., Any]] | None = None,
    *,
    skills: list[type] | None = None,
    sub_agents: dict[str, Agent] | None = None,
    system_prompt: str | None = None,
    task_queue: str = TEMPORAL_TASK_QUEUE,
    max_steps: int = 20,
    context_limit: int = CONTEXT_LIMIT,
    temporal_host: str = TEMPORAL_HOST,
    temporal_namespace: str = TEMPORAL_NAMESPACE,
) -> Agent:
    """Worker-side factory that registers tools and returns an Agent.

    Parameters
    ----------
    model:
        Model identifier in the format "openai:<model-name>".
    tools:
        List of functions decorated with @tool.
    skills:
        Optional list of classes decorated with @skill.  Each skill's tools
        are registered into ToolRegistry and its system_prompt fragment is
        appended to *system_prompt*.
    sub_agents:
        Optional mapping of sub-agent name → Agent.  For each entry the
        task-queue mapping is stored in AgentConfig and registered into
        ToolRegistry so that create_plan can reference sub-agents by name.
    system_prompt:
        Optional system message prepended to every LLM call.
    task_queue:
        Temporal task queue name.
    max_steps:
        Maximum plan items before the workflow fails.
    context_limit:
        Estimated-token threshold that triggers context summarisation.
    temporal_host:
        Temporal server address.
    temporal_namespace:
        Temporal namespace.

    Raises
    ------
    ValueError
        If model uses an unsupported provider prefix, or a skill is missing
        required attributes.
    """
    if not any(model.startswith(prefix) for prefix in _SUPPORTED_PREFIXES):
        supported = ", ".join(_SUPPORTED_PREFIXES)
        raise ValueError(
            f"Unsupported model prefix in {model!r}. "
            f"Supported prefixes: {supported}"
        )

    # Validate and register explicit tools.
    tool_names: list[str] = []
    for func in (tools or []):
        entry = getattr(func, "__tool_entry__", None)
        if entry is None:
            raise ValueError(
                f"Function {func.__name__!r} was not decorated with @tool. "
                "All tools must be decorated before being passed to create_durable_agent()."
            )
        tool_names.append(entry.name)

    # Validate skills and collect their tools + prompt fragments.
    skill_prompt_parts: list[str] = []
    for skill_cls in (skills or []):
        if not getattr(skill_cls, "__is_skill__", False):
            raise ValueError(
                f"Class {skill_cls.__name__!r} was not decorated with @skill."
            )
        if not hasattr(skill_cls, "tools"):
            raise ValueError(
                f"Skill {skill_cls.__name__!r} is missing required class attribute 'tools'."
            )
        if not hasattr(skill_cls, "system_prompt"):
            raise ValueError(
                f"Skill {skill_cls.__name__!r} is missing required class attribute 'system_prompt'."
            )
        for func in skill_cls.tools:
            entry = getattr(func, "__tool_entry__", None)
            if entry is None:
                raise ValueError(
                    f"Skill tool {func.__name__!r} in {skill_cls.__name__!r} "
                    "was not decorated with @tool."
                )
            if entry.name not in tool_names:
                tool_names.append(entry.name)
            # Tools decorated with @tool are already registered in the
            # module-level registry at decoration time — no need to re-register.
        skill_prompt_parts.append(skill_cls.system_prompt)

    # Build combined system prompt.
    combined_prompt: str | None = system_prompt
    if skill_prompt_parts:
        if combined_prompt:
            combined_prompt = combined_prompt + "\n\n" + "\n\n".join(skill_prompt_parts)
        else:
            combined_prompt = "\n\n".join(skill_prompt_parts)

    # Build sub-agent task-queue map.  This map (stored on AgentConfig) is the
    # single source of truth for delegation: create_plan resolves sub-agents
    # ONLY from the calling agent's own config, never from a global registry,
    # so an agent can never delegate to a sub-agent it was not given.
    sub_agent_task_queues: dict[str, str] = {}
    for name, agent in (sub_agents or {}).items():
        sub_agent_task_queues[name] = agent.config.task_queue

    config = AgentConfig(
        model=model,
        task_queue=task_queue,
        system_prompt=combined_prompt,
        max_steps=max_steps,
        context_limit=context_limit,
        temporal_host=temporal_host,
        temporal_namespace=temporal_namespace,
        sub_agent_task_queues=sub_agent_task_queues,
        tool_names=tool_names,
    )

    set_agent_config(config)
    return Agent(config=config)
