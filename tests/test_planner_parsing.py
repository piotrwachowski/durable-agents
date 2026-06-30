"""Tests for create_plan parsing and its recoverable fallbacks.

The OpenAI client is monkeypatched so no network call is made; we exercise the
activity's own parsing/fallback logic deterministically.
"""
from __future__ import annotations

import json
import types
from unittest.mock import AsyncMock

from durable_agents.activities import planner
from durable_agents.models import Plan


class _Msg:
    def __init__(self, tool_calls=None, content=None):
        self.tool_calls = tool_calls
        self.content = content


class _Choice:
    def __init__(self, message):
        self.message = message


class _Resp:
    def __init__(self, message):
        self.choices = [_Choice(message)]


def _tool_call(name: str, arguments: str, call_id: str = "call_1"):
    return types.SimpleNamespace(
        id=call_id,
        function=types.SimpleNamespace(name=name, arguments=arguments),
    )


def _patch_create(monkeypatch, response: _Resp) -> None:
    monkeypatch.setattr(
        planner._client.chat.completions,
        "create",
        AsyncMock(return_value=response),
    )


async def test_no_tool_call_falls_back_to_single_wait_item(monkeypatch) -> None:
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=None)))
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert isinstance(plan, Plan)
    assert len(plan.items) == 1
    assert plan.items[0].type == "wait"


async def test_malformed_json_falls_back(monkeypatch) -> None:
    bad = _Resp(_Msg(tool_calls=[_tool_call("write_plan", "{not valid json")]))
    _patch_create(monkeypatch, bad)
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert len(plan.items) == 1
    assert plan.items[0].title == "Execute task"


async def test_valid_plan_is_parsed(monkeypatch) -> None:
    args = json.dumps(
        {"items": [{"id": 1, "title": "Step", "description": "d", "type": "tool_call"}]}
    )
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=[_tool_call("write_plan", args)])))
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert len(plan.items) == 1
    assert plan.items[0].type == "tool_call"
    assert plan.items[0].title == "Step"


async def test_delegate_to_unknown_subagent_is_coerced_to_tool_call(monkeypatch) -> None:
    # With no agent config in this context, no sub-agent resolves, so a
    # delegate item must be coerced to a normal tool_call rather than raising.
    args = json.dumps(
        {
            "items": [
                {
                    "id": 1,
                    "title": "Hand off",
                    "description": "d",
                    "type": "delegate",
                    "sub_agent_name": "ghost",
                }
            ]
        }
    )
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=[_tool_call("write_plan", args)])))
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert plan.items[0].type == "tool_call"
    assert plan.items[0].sub_agent_name is None
    assert plan.items[0].sub_task_queue is None


async def test_plan_recovered_from_text_content(monkeypatch) -> None:
    # Models served via Ollama may emit the tool call as plain-text JSON in
    # `content` (often wrapped in <think> reasoning) instead of tool_calls.
    payload = json.dumps(
        {
            "name": "write_plan",
            "arguments": {
                "items": [
                    {"id": 1, "title": "Step", "description": "d", "type": "tool_call"}
                ]
            },
        }
    )
    content = f"<think>let me plan this</think>\n{payload}"
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=None, content=content)))
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert len(plan.items) == 1
    assert plan.items[0].type == "tool_call"
    assert plan.items[0].title == "Step"


async def test_plan_recovered_from_bare_arguments_object(monkeypatch) -> None:
    # Some models emit just the arguments object, without the name wrapper.
    content = json.dumps(
        {"items": [{"id": 1, "title": "Bare", "description": "d", "type": "wait"}]}
    )
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=None, content=content)))
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert plan.items[0].title == "Bare"


async def test_structured_tool_call_takes_precedence_over_content(monkeypatch) -> None:
    # When tool_calls is populated, the content fallback must NOT be consulted.
    args = json.dumps(
        {"items": [{"id": 1, "title": "Structured", "description": "d", "type": "wait"}]}
    )
    junk_content = json.dumps(
        {"items": [{"id": 9, "title": "FromContent", "description": "d", "type": "wait"}]}
    )
    _patch_create(
        monkeypatch,
        _Resp(_Msg(tool_calls=[_tool_call("write_plan", args)], content=junk_content)),
    )
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert plan.items[0].title == "Structured"


async def test_plan_unrecoverable_content_falls_back_to_wait(monkeypatch) -> None:
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=None, content="no json here")))
    plan = await planner.create_plan("do x", "openai:gpt-4o-mini", None)
    assert len(plan.items) == 1
    assert plan.items[0].type == "wait"


async def test_execute_item_recovers_tool_call_from_content(monkeypatch) -> None:
    payload = json.dumps({"name": "complete_item", "arguments": {"output": "done"}})
    content = f"<think>reasoning</think>{payload}"
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=None, content=content)))
    from durable_agents.models import TodoItem

    item = TodoItem(id=1, title="t", description="d", type="tool_call")
    result = await planner.execute_plan_item(item, [], "openai:gpt-4o-mini", None)
    assert result.output == "done"
    assert result.tool_name is None


async def test_execute_item_plain_text_is_completion(monkeypatch) -> None:
    _patch_create(monkeypatch, _Resp(_Msg(tool_calls=None, content="just prose")))
    from durable_agents.models import TodoItem

    item = TodoItem(id=1, title="t", description="d", type="wait")
    result = await planner.execute_plan_item(item, [], "openai:gpt-4o-mini", None)
    assert result.output == "just prose"
    assert result.tool_name is None

