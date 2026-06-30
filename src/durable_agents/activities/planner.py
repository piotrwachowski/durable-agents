from __future__ import annotations

import json

from openai import AsyncOpenAI
from temporalio import activity

from durable_agents.config import LLM_MAX_TOKENS, OPENAI_API_KEY, OPENAI_BASE_URL
from durable_agents.harness.registry import registry
from durable_agents.harness.state import get_agent_config
from durable_agents.models import ItemResult, Plan, TodoItem

# Module-level client — created outside workflow code (determinism safe).
# OPENAI_BASE_URL (when set) targets an OpenAI-compatible server such as Ollama
# or vLLM; left empty it defaults to the OpenAI cloud endpoint.
_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)

# Provider prefixes that _model_name() should strip. Ollama/vLLM model tags may
# themselves contain a colon (quantization, e.g. ':Q4_K_M'), so only these known
# prefixes are removed.
_KNOWN_PROVIDER_PREFIXES = frozenset({"openai"})


def _model_name(model: str) -> str:
    """Strip a leading provider prefix, e.g. 'openai:gpt-4o-mini' -> 'gpt-4o-mini'.

    Only a recognised provider prefix is stripped, so Ollama-style tags that embed
    a quantization after a colon (e.g. 'org/model:Q4_K_M') are preserved intact.
    """
    prefix, sep, rest = model.partition(":")
    if sep and prefix in _KNOWN_PROVIDER_PREFIXES:
        return rest
    return model


# -- Schema helpers -----------------------------------------------------------

_WRITE_PLAN_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "write_plan",
        "description": (
            "Write a structured plan as an ordered list of todo items. "
            "Each item should be a concrete, actionable step."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "description": "1-based item index"},
                            "title": {"type": "string", "description": "Short action label"},
                            "description": {
                                "type": "string",
                                "description": "Detailed description of what to do",
                            },
                            "type": {
                                "type": "string",
                                "enum": ["tool_call", "delegate", "wait"],
                                "description": (
                                    "tool_call: requires a tool invocation; "
                                    "delegate: hand off to a named sub-agent; "
                                    "wait: pure reasoning / no tool needed"
                                ),
                            },
                            "sub_agent_name": {
                                "type": "string",
                                "description": (
                                    "Name of the sub-agent to delegate to. "
                                    "Required when type is 'delegate'."
                                ),
                            },
                        },
                        "required": ["id", "title", "description", "type"],
                    },
                }
            },
            "required": ["items"],
        },
    },
}

_COMPLETE_ITEM_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "complete_item",
        "description": (
            "Complete the current todo item with a direct result "
            "(use when no tool invocation is needed)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "output": {
                    "type": "string",
                    "description": "The result or reasoning for this item.",
                },
            },
            "required": ["output"],
        },
    },
}


# -- Activities ---------------------------------------------------------------


@activity.defn
async def create_plan(
    task: str, model: str, system_prompt: str | None
) -> Plan:
    """Phase 1 -- ask the LLM to produce a structured todo list for *task*.

    Tools and sub-agents are scoped to the current agent's config (read from
    the process-local state via activity.info().task_queue) so that child
    agents cannot see — or recurse into — each other's sub-agents.
    """
    # Scope tools and sub-agents to THIS agent's config.
    config = get_agent_config()  # auto-detects task_queue from activity context
    tool_schemas = registry.to_openai_tools(config.tool_names if config else None)
    sub_agent_names = list(config.sub_agent_task_queues.keys()) if config else []

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    tool_list_text = (
        "\n".join(
            f"- {t['function']['name']}: {t['function']['description']}"
            for t in tool_schemas
        )
        if tool_schemas
        else "(no tools available)"
    )

    # Build sub-agent section with optional one-line descriptions.
    sub_agent_section = ""
    if sub_agent_names:
        lines: list[str] = []
        for name in sub_agent_names:
            description = ""
            if config and name in config.sub_agent_task_queues:
                sub_tq = config.sub_agent_task_queues[name]
                sub_cfg = get_agent_config(sub_tq)
                if sub_cfg and sub_cfg.system_prompt:
                    description = ": " + sub_cfg.system_prompt[:80].split("\n")[0]
            lines.append(f"- {name}{description}")
        sub_agent_section = (
            "\n\nAvailable sub-agents (use type='delegate' with sub_agent_name):\n"
            + "\n".join(lines)
        )

    messages.append({
        "role": "user",
        "content": (
            f"Task: {task}\n\n"
            f"Available tools:\n{tool_list_text}"
            f"{sub_agent_section}\n\n"
            "Create a step-by-step plan to complete this task. "
            "Call write_plan with your ordered list of todo items."
        ),
    })

    response = await _client.chat.completions.create(  # type: ignore[call-overload]
        model=_model_name(model),
        max_tokens=LLM_MAX_TOKENS,
        messages=messages,  # type: ignore[arg-type]
        tools=[_WRITE_PLAN_SCHEMA],  # type: ignore[arg-type]
        tool_choice={"type": "function", "function": {"name": "write_plan"}},
    )

    tool_call = response.choices[0].message.tool_calls
    if not tool_call:
        return Plan(items=[TodoItem(id=1, title="Execute task", description=task, type="wait")])

    try:
        args = json.loads(tool_call[0].function.arguments or "{}")
    except json.JSONDecodeError:
        # Truncated/malformed plan JSON — fall back to a single execute step
        # rather than crashing the planning activity.
        return Plan(items=[TodoItem(id=1, title="Execute task", description=task, type="wait")])

    # Resolve sub-agent task queues ONLY from this agent's own config, never
    # from the process-global registry — otherwise an agent could delegate to a
    # sub-agent it was never given, causing unintended recursion.
    sub_agent_task_queues = config.sub_agent_task_queues if config else {}

    items: list[TodoItem] = []
    for item in args.get("items", []):
        item_type = item.get("type", "wait")
        sub_agent_name = item.get("sub_agent_name")
        sub_task_queue = (
            sub_agent_task_queues.get(sub_agent_name) if sub_agent_name else None
        )

        # The model sometimes marks an item as 'delegate' while naming a *tool*
        # (e.g. read_file) or an unknown sub-agent. A delegate item is only
        # valid when its name resolves to a configured sub-agent; otherwise we
        # coerce it to a normal tool_call so the ReAct loop can handle it inline
        # instead of the workflow raising on an unresolved sub-agent.
        if item_type == "delegate" and sub_task_queue is None:
            item_type = "tool_call"
            sub_agent_name = None

        items.append(
            TodoItem(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                type=item_type,
                status="pending",
                sub_agent_name=sub_agent_name,
                sub_task_queue=sub_task_queue,
            )
        )

    if not items:
        items = [TodoItem(id=1, title="Execute task", description=task, type="wait")]

    return Plan(items=items)


@activity.defn
async def execute_plan_item(
    item: TodoItem,
    history: list[dict],
    model: str,
    system_prompt: str | None,
) -> ItemResult:
    """Phase 2 -- ask the LLM what to do next for a single todo item.

    This is one turn of a ReAct loop driven by the workflow.  The LLM may:
      * call a registered tool  -> returns ItemResult(tool_name=..., tool_args=...,
        tool_call_id=...); the workflow dispatches the tool, appends the result
        to *history*, and calls this activity again.
      * call complete_item      -> returns the final ItemResult for this item.
      * return plain text        -> treated as completion.

    Tool schemas are read from the local registry -- never from the input.
    """
    config = get_agent_config()
    tool_schemas = registry.to_openai_tools(config.tool_names if config else None)
    all_tools = tool_schemas + [_COMPLETE_ITEM_SCHEMA]

    # history already starts with the system message (if any) prepended by the
    # workflow, plus the running task/tool messages.  Only add the per-item
    # instruction on the first turn (when no tool message for this item exists
    # yet); on later turns the accumulated tool results carry the context.
    messages: list[dict] = list(history)
    messages.append({
        "role": "user",
        "content": (
            f"Current todo item -- {item.title}\n"
            f"Description: {item.description}\n\n"
            "Call a tool to make progress, or call complete_item when this item is "
            "fully done. You may call tools multiple times across turns before "
            "completing."
        ),
    })

    response = await _client.chat.completions.create(
        model=_model_name(model),
        max_tokens=LLM_MAX_TOKENS,
        messages=messages,  # type: ignore[arg-type]
        tools=all_tools,  # type: ignore[arg-type]
    )

    choice = response.choices[0]
    tool_calls = choice.message.tool_calls

    if not tool_calls:
        content = choice.message.content or ""
        return ItemResult(item_id=item.id, output=content)

    called = tool_calls[0]
    fn_name = called.function.name  # type: ignore[union-attr]

    # The model occasionally emits malformed or truncated JSON for the tool
    # arguments (most often when a single call — e.g. write_file with a whole
    # file's contents — exceeds max_tokens and gets cut off mid-string). Treat
    # that as a recoverable observation rather than crashing the activity so the
    # ReAct loop can retry with a well-formed / smaller call.
    try:
        fn_args = json.loads(called.function.arguments or "{}")  # type: ignore[union-attr]
    except json.JSONDecodeError:
        fn_args = None

    if fn_name == "complete_item":
        output = fn_args.get("output", "") if isinstance(fn_args, dict) else ""
        return ItemResult(item_id=item.id, output=output)

    if fn_args is None:
        # Hand the call to the workflow with empty args; dispatch_tool will
        # surface the resulting error as a tool observation the model can react
        # to on the next turn instead of failing the workflow.
        fn_args = {}

    # Resolve per-tool execution options (if any) from the registry so the
    # workflow can apply them deterministically from event history.
    entry = registry.get(fn_name)
    tool_timeout_seconds = entry.timeout_seconds if entry else None
    tool_max_retries = entry.max_retries if entry else None

    # The LLM chose a registered tool.  Return the call id so the workflow can
    # thread a matching role="tool" message back into history.
    return ItemResult(
        item_id=item.id,
        output="",  # filled in by workflow after dispatch_tool
        tool_name=fn_name,
        tool_args=fn_args,
        tool_call_id=called.id,
        tool_timeout_seconds=tool_timeout_seconds,
        tool_max_retries=tool_max_retries,
    )


@activity.defn
async def synthesize_result(
    plan: Plan,
    history: list[dict],
    model: str,
    system_prompt: str | None,
) -> str:
    """Phase 3 -- synthesise a final answer from the completed plan and history."""
    completed_summary = "\n".join(
        f"{i.id}. {i.title}: {i.description}"
        for i in plan.items
        if i.status == "done"
    )

    # history already starts with the system message (if any) prepended by
    # the workflow — do not add it again.
    messages: list[dict] = list(history)

    messages.append({
        "role": "user",
        "content": (
            f"All todo items are complete:\n{completed_summary}\n\n"
            "Please write a clear, comprehensive final answer based on the work done above."
        ),
    })

    response = await _client.chat.completions.create(
        model=_model_name(model),
        max_tokens=LLM_MAX_TOKENS,
        messages=messages,  # type: ignore[arg-type]
    )

    return response.choices[0].message.content or ""


@activity.defn
async def prepare_delegation(
    item: TodoItem,
    history: list[dict],
    model: str,
    system_prompt: str | None,
) -> str:
    """Craft a precise, self-contained task message for a sub-agent.

    The parent (orchestrator) holds the conversation history; at delegation
    time it distills exactly what the sub-agent needs into a standalone task
    message.  This preserves context isolation -- the child workflow starts
    with a clean, targeted task and never sees the parent's full history.
    """
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history)
    messages.append({
        "role": "user",
        "content": (
            f"You are about to delegate to the {item.sub_agent_name!r} sub-agent.\n"
            f"Original intent for this step: {item.description}\n\n"
            "Using the context above, write a precise, self-contained task message "
            "for this sub-agent. Include every specific detail it will need "
            "(file paths, prior findings, concrete results) so it can work without "
            "any access to this conversation. Reply with ONLY the task message text."
        ),
    })

    response = await _client.chat.completions.create(
        model=_model_name(model),
        max_tokens=LLM_MAX_TOKENS,
        messages=messages,  # type: ignore[arg-type]
    )
    return response.choices[0].message.content or item.description
