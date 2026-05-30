"""Tests for the create_durable_agent factory and its validation."""
from __future__ import annotations

import pytest

from durable_agents import create_durable_agent, skill, tool


@tool
async def factory_tool_a(x: str) -> str:
    """A factory tool."""
    return x


def test_unsupported_model_prefix_rejected() -> None:
    with pytest.raises(ValueError):
        create_durable_agent(model="anthropic:claude-3", task_queue="tq-prefix")


def test_undecorated_tool_rejected() -> None:
    async def not_a_tool(x: str) -> str:
        return x

    with pytest.raises(ValueError):
        create_durable_agent(
            model="openai:gpt-4o-mini",
            tools=[not_a_tool],  # type: ignore[list-item]
            task_queue="tq-undecorated",
        )


def test_config_is_built_from_arguments() -> None:
    agent = create_durable_agent(
        model="openai:gpt-4o-mini",
        tools=[factory_tool_a],
        system_prompt="Base prompt.",
        task_queue="tq-config",
        max_steps=7,
    )
    cfg = agent.config
    assert cfg.model == "openai:gpt-4o-mini"
    assert "factory_tool_a" in cfg.tool_names
    assert cfg.max_steps == 7
    assert cfg.system_prompt == "Base prompt."


def test_skill_prompt_is_merged() -> None:
    @skill
    class GoodSkill:
        tools = [factory_tool_a]
        system_prompt = "Skill prompt fragment."

    agent = create_durable_agent(
        model="openai:gpt-4o-mini",
        skills=[GoodSkill],
        system_prompt="Base prompt.",
        task_queue="tq-skill",
    )
    assert "Base prompt." in agent.config.system_prompt
    assert "Skill prompt fragment." in agent.config.system_prompt


def test_skill_missing_attributes_rejected() -> None:
    @skill
    class BadSkill:
        pass

    with pytest.raises(ValueError):
        create_durable_agent(
            model="openai:gpt-4o-mini",
            skills=[BadSkill],
            task_queue="tq-bad-skill",
        )


def test_sub_agents_task_queue_map() -> None:
    sub = create_durable_agent(model="openai:gpt-4o-mini", task_queue="sub-tq")
    parent = create_durable_agent(
        model="openai:gpt-4o-mini",
        sub_agents={"helper": sub},
        task_queue="parent-tq",
    )
    assert parent.config.sub_agent_task_queues == {"helper": "sub-tq"}
