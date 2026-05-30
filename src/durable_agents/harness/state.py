from __future__ import annotations

from temporalio import activity

from durable_agents.models import AgentConfig

# Process-local registry set by create_durable_agent() on the worker side.
# Keyed by task_queue so multiple workers can coexist in the same process.
# Activities and the workflow read agent identity (model, system_prompt, etc.)
# from here instead of from AgentInput, so that these details never cross the
# Temporal wire.
_agent_configs: dict[str, AgentConfig] = {}


def set_agent_config(config: AgentConfig) -> None:
    _agent_configs[config.task_queue] = config


def get_agent_config(task_queue: str | None = None) -> AgentConfig | None:
    """Return the AgentConfig for the given task_queue.

    If *task_queue* is not provided, attempts to auto-detect it from the
    current activity context via ``activity.info().task_queue``.  Call with
    an explicit *task_queue* (e.g. ``workflow.info().task_queue``) from
    workflow code where the activity context is not available.
    """
    if task_queue is not None:
        return _agent_configs.get(task_queue)
    try:
        tq = activity.info().task_queue
    except RuntimeError:
        # Not called from an activity context — caller should pass task_queue.
        return None
    return _agent_configs.get(tq)
