# 7. Skills

> **On this page:** [What is a skill](#what-is-a-skill) · [Defining a skill](#defining-a-skill) · [Attaching skills to an agent](#attaching-skills-to-an-agent) · [Skills vs. tools vs. sub-agents](#skills-vs-tools-vs-sub-agents)

## What is a skill

A **skill** is a reusable bundle of *tools plus a prompt fragment* that you can
attach to any agent. Where a single `@tool` adds one capability, a skill packages
a coherent set of capabilities together with the instructions that tell the model
how and when to use them.

Skills are how you share agent behaviour across projects without copy-pasting
tool lists and prompt snippets.

## Defining a skill

Decorate a class with `@skill`. The class must declare two attributes:

- `tools` — a list of functions decorated with [`@tool`](05-tools.md)
- `system_prompt` — a string fragment appended to the agent's base prompt

```python
from durable_agents import skill, tool

@tool
async def read_file(path: str) -> str:
    """Read a text file."""
    ...

@tool
async def write_file(path: str, content: str) -> str:
    """Write text to a file."""
    ...

@skill
class FilesystemSkill:
    tools = [read_file, write_file]
    system_prompt = (
        "You can read and write files. Always confirm a path exists "
        "before writing, and never overwrite without reason."
    )
```

The `@skill` decorator simply marks the class (`__is_skill__ = True`) so that
`create_durable_agent` can validate it. **Decoration alone does not register
anything** — a skill is only activated when passed to an agent.

## Attaching skills to an agent

Pass skills via the `skills` parameter. Their tools are registered into the
worker's [tool registry](05-tools.md#the-tool-registry) and their prompt
fragments are appended to the agent's `system_prompt`:

```python
agent = create_durable_agent(
    model="openai:gpt-4o-mini",
    skills=[FilesystemSkill],
    system_prompt="You are a coding assistant.",
    task_queue="coding-agent",
)
```

You can combine `skills` with standalone `tools` and with `sub_agents` freely;
all of their tools end up in the same registry on the worker.

## Skills vs. tools vs. sub-agents

These three composition mechanisms solve different problems:

| Mechanism | Granularity | Adds | Use when |
|---|---|---|---|
| [`@tool`](05-tools.md) | One action | A single capability + schema | The agent needs one more thing it can *do*. |
| `@skill` | A capability bundle | Several tools + a prompt fragment | A coherent set of tools is reused across agents. |
| [Sub-agents](06-sub-agents.md) | A whole agent | An independent, delegated worker | A task deserves its own model, prompt, and isolated context. |

Rule of thumb: reach for a **tool** for a single action, a **skill** to package
related tools with guidance, and a **sub-agent** when the work warrants a
separate, independently-scalable specialist.

Next: [Architecture](08-architecture.md).
