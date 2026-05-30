from __future__ import annotations

import json
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# All activity imports MUST be wrapped so that the workflow sandbox does not
# execute the module-level side-effects (AsyncOpenAI client init, registry
# population) during replay.
with workflow.unsafe.imports_passed_through():
    from durable_agents.activities.context import summarise_context
    from durable_agents.activities.dispatcher import dispatch_tool
    from durable_agents.activities.planner import (
        create_plan,
        execute_plan_item,
        prepare_delegation,
        synthesize_result,
    )
    from durable_agents.config import CONTEXT_LIMIT
    from durable_agents.harness.state import get_agent_config
    from durable_agents.models import AgentInput, ItemResult, Plan, TodoItem


# Rough chars-per-token heuristic used to estimate history size without
# importing tiktoken (not available in all environments).
_CHARS_PER_TOKEN = 4

# Maximum tool invocations the LLM may make while working a single todo item
# before the workflow forces completion. Prevents an item from looping forever.
_MAX_TOOL_ITERATIONS = 8

# Default activity timeout for a tool dispatch when the tool sets no explicit
# timeout via @tool(timeout_seconds=...).
_DEFAULT_TOOL_TIMEOUT_SECONDS = 300


def _estimate_tokens(history: list[dict]) -> int:
    total_chars = sum(len(m.get("content") or "") for m in history)
    return total_chars // _CHARS_PER_TOKEN


@workflow.defn
class AgentWorkflow:
    """Three-phase plan-then-execute agent workflow.

    Phase 1: create_plan    -- LLM produces a structured todo list
    Phase 2: execute loop   -- iterate over items, dispatch tools, optional replan
    Phase 3: synthesize_result -- LLM writes the final answer
    """

    def __init__(self) -> None:
        self._plan: Plan = Plan(items=[])

    @workflow.query
    def get_todo_list(self) -> list[TodoItem]:
        """Return current plan items; empty list before planning completes."""
        return list(self._plan.items)

    @workflow.run
    async def run(self, agent_input: AgentInput) -> str:
        config = get_agent_config(workflow.info().task_queue)
        default_model = "openai:gpt-4o-mini"
        model: str = agent_input.model_override or (config.model if config else default_model)
        system_prompt: str | None = config.system_prompt if config else None
        max_steps: int = agent_input.max_steps
        context_limit: int = config.context_limit if config else CONTEXT_LIMIT

        history: list[dict] = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})
        history.append({"role": "user", "content": agent_input.task})

        # ── Phase 1: planning ────────────────────────────────────────────────
        self._plan = await workflow.execute_activity(
            create_plan,
            args=[agent_input.task, model, system_prompt],
            start_to_close_timeout=timedelta(seconds=120),
        )

        # ── Phase 2: execution loop ──────────────────────────────────────────
        # Use a while loop so that items added by replan() are picked up.
        steps_taken = 0
        delegate_count = 0

        while True:
            pending = [i for i in self._plan.items if i.status == "pending"]
            if not pending:
                break

            item = pending[0]

            # Max steps guard (applies to every kind of item).
            if steps_taken >= max_steps:
                raise ApplicationError(f"Exceeded max_steps={max_steps}")

            # ── Delegation: hand off to a sub-agent child workflow ────────────
            if item.type == "delegate":
                # sub_task_queue is resolved by create_plan from THIS agent's
                # own config (never the global registry), so it is trustworthy.
                sub_task_queue: str | None = item.sub_task_queue
                if not sub_task_queue:
                    raise ApplicationError(
                        f"Unknown sub-agent {item.sub_agent_name!r}: "
                        "no task queue was resolved at plan time. Ensure the "
                        "sub-agent is configured on this agent before starting "
                        "the worker."
                    )
                item.status = "in_progress"
                delegate_count += 1

                # Distill a precise, self-contained task for the child from the
                # parent's running history. This is where prior results (e.g. the
                # archaeologist's findings) flow into the next sub-agent — the
                # child still starts with a clean, isolated context.
                crafted_task: str = await workflow.execute_activity(
                    prepare_delegation,
                    args=[item, history, model, system_prompt],
                    start_to_close_timeout=timedelta(seconds=120),
                )

                child_id = (
                    f"{workflow.info().workflow_id}-{item.sub_agent_name}-{delegate_count}"
                )
                child_result: str = await workflow.execute_child_workflow(
                    AgentWorkflow.run,
                    AgentInput(
                        task=crafted_task,
                        model_override=agent_input.model_override,
                        max_steps=max_steps,
                    ),
                    id=child_id,
                    task_queue=sub_task_queue,
                )
                history.append({
                    "role": "assistant",
                    "content": (
                        f"[{item.title}] Delegated to {item.sub_agent_name!r} → {child_result}"
                    ),
                })
                item.status = "done"
                steps_taken += 1
                continue

            # ── Tool / reasoning item: per-item ReAct inner loop ─────────────
            item.status = "in_progress"

            # Context summarisation check before working the item.
            if _estimate_tokens(history) > context_limit:
                history = await workflow.execute_activity(
                    summarise_context,
                    history,
                    start_to_close_timeout=timedelta(seconds=120),
                )

            # Working copy of history for this item; tool calls/results are
            # threaded in here so the LLM can act on tool output across turns.
            item_history: list[dict] = list(history)
            final_output: str = ""

            for _ in range(_MAX_TOOL_ITERATIONS):
                item_result: ItemResult = await workflow.execute_activity(
                    execute_plan_item,
                    args=[item, item_history, model, system_prompt],
                    start_to_close_timeout=timedelta(seconds=120),
                )

                # No tool requested → the item is complete.
                if not item_result.tool_name:
                    final_output = item_result.output
                    break

                # Dispatch the requested tool as its own durable activity.
                # Per-tool timeout / retries (from @tool options) are applied
                # here; they arrive via ItemResult so they are deterministic on
                # replay. Defaults are used when a tool sets no options.
                tool_timeout = timedelta(
                    seconds=item_result.tool_timeout_seconds or _DEFAULT_TOOL_TIMEOUT_SECONDS
                )
                tool_retry_policy: RetryPolicy | None = (
                    RetryPolicy(maximum_attempts=item_result.tool_max_retries)
                    if item_result.tool_max_retries is not None
                    else None
                )
                tool_output: str = await workflow.execute_activity(
                    dispatch_tool,
                    args=[item_result.tool_name, item_result.tool_args],
                    start_to_close_timeout=tool_timeout,
                    retry_policy=tool_retry_policy,
                )

                # Thread the tool call + result back so the next turn sees them.
                item_history.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": item_result.tool_call_id,
                        "type": "function",
                        "function": {
                            "name": item_result.tool_name,
                            "arguments": json.dumps(item_result.tool_args or {}),
                        },
                    }],
                })
                item_history.append({
                    "role": "tool",
                    "tool_call_id": item_result.tool_call_id,
                    "content": tool_output,
                })
            else:
                # Loop exhausted without an explicit completion.
                final_output = (
                    "(item reached the maximum number of tool iterations "
                    "without an explicit completion)"
                )

            history.append({
                "role": "assistant",
                "content": f"[{item.title}] {final_output}",
            })
            item.status = "done"
            steps_taken += 1

        # ── Phase 3: synthesis ───────────────────────────────────────────────
        return await workflow.execute_activity(
            synthesize_result,
            args=[self._plan, history, model, system_prompt],
            start_to_close_timeout=timedelta(seconds=120),
        )
