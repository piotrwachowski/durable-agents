from __future__ import annotations

import uuid

from temporalio.client import Client

from durable_agents.config import (
    TEMPORAL_HOST,
    TEMPORAL_NAMESPACE,
)
from durable_agents.models import AgentInput


class DurableAgentClient:
    """Thin client for triggering an :class:`AgentWorkflow`.

    Does not require importing any tool modules — only the task queue name and
    the task string are needed.

    Parameters
    ----------
    task_queue:
        The Temporal task queue the worker is polling.
    temporal_host:
        Temporal server address (host:port).
    namespace:
        Temporal namespace.
    """

    def __init__(
        self,
        task_queue: str,
        temporal_host: str = TEMPORAL_HOST,
        namespace: str = TEMPORAL_NAMESPACE,
    ) -> None:
        self._task_queue = task_queue
        self._temporal_host = temporal_host
        self._namespace = namespace

    async def run(
        self,
        task: str,
        *,
        workflow_id: str | None = None,
        model_override: str | None = None,
        max_steps: int | None = None,
    ) -> str:
        """Start ``AgentWorkflow`` and return the final answer string.

        Parameters
        ----------
        task:
            Natural-language task for the agent.
        workflow_id:
            Optional stable identifier for idempotency.  Defaults to a random
            UUID.  If the ID already exists, ``WorkflowAlreadyStartedError``
            is raised without starting a duplicate workflow.
        model_override:
            Override the model declared in ``AgentConfig`` for this run.
        max_steps:
            Override the max steps limit for this run.
        """
        from durable_agents.workflows.agent_workflow import AgentWorkflow

        if workflow_id is None:
            workflow_id = f"{self._task_queue}-{uuid.uuid4()}"

        agent_input = AgentInput(
            task=task,
            model_override=model_override,
            max_steps=max_steps if max_steps is not None else 20,
        )

        client = await Client.connect(self._temporal_host, namespace=self._namespace)

        # WorkflowAlreadyStartedError surfaced as-is — caller decides how to handle.
        result: str = await client.execute_workflow(
            AgentWorkflow.run,
            agent_input,
            id=workflow_id,
            task_queue=self._task_queue,
        )
        return result
