"""End-to-end workflow test running the real AgentWorkflow.

The LLM/tool activities are replaced with deterministic stubs registered under
the same activity names, so the genuine plan-then-execute loop (planning →
per-item ReAct turns → tool dispatch threading → synthesis) is exercised against
a real Temporal test environment — proving the durable control flow without any
network access.

If the Temporal test server binary cannot be started (e.g. fully offline first
run), the test skips rather than failing.
"""
from __future__ import annotations

import uuid

import pytest
from temporalio import activity
from temporalio.worker import Worker

from durable_agents.models import AgentInput, ItemResult, Plan, RuntimeConfig, TodoItem
from durable_agents.workflows.agent_workflow import AgentWorkflow


@activity.defn(name="load_runtime_config")
async def stub_load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(model="openai:gpt-4o-mini", system_prompt=None, context_limit=6000)


@activity.defn(name="create_plan")
async def stub_create_plan(task, model, system_prompt) -> Plan:
    return Plan(
        items=[TodoItem(id=1, title="Search", description="search the web", type="tool_call")]
    )


@activity.defn(name="execute_plan_item")
async def stub_execute_plan_item(item, history, model, system_prompt) -> ItemResult:
    item_id = item["id"] if isinstance(item, dict) else item.id
    # Second turn: a tool observation is present in history -> complete the item.
    if any(isinstance(m, dict) and m.get("role") == "tool" for m in history):
        return ItemResult(item_id=item_id, output="search complete")
    # First turn: request a tool call.
    return ItemResult(
        item_id=item_id,
        output="",
        tool_name="web_search",
        tool_args={"q": "answer"},
        tool_call_id="call_1",
    )


@activity.defn(name="dispatch_tool")
async def stub_dispatch_tool(tool_name, tool_args) -> str:
    return "RESULT: 42"


@activity.defn(name="synthesize_result")
async def stub_synthesize_result(plan, history, model, system_prompt) -> str:
    return "FINAL ANSWER: 42"


@activity.defn(name="prepare_delegation")
async def stub_prepare_delegation(item, history, model, system_prompt) -> str:
    return "delegated task"


@activity.defn(name="summarise_context")
async def stub_summarise_context(history):
    return history


async def test_agent_workflow_runs_full_loop() -> None:
    try:
        from temporalio.testing import WorkflowEnvironment

        env = await WorkflowEnvironment.start_time_skipping()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Temporal test server unavailable: {exc}")

    async with env:
        task_queue = f"test-{uuid.uuid4()}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[AgentWorkflow],
            activities=[
                stub_load_runtime_config,
                stub_create_plan,
                stub_execute_plan_item,
                stub_dispatch_tool,
                stub_synthesize_result,
                stub_prepare_delegation,
                stub_summarise_context,
            ],
        ):
            result = await env.client.execute_workflow(
                AgentWorkflow.run,
                AgentInput(task="what is the answer?"),
                id=f"wf-{uuid.uuid4()}",
                task_queue=task_queue,
            )

    assert result == "FINAL ANSWER: 42"
