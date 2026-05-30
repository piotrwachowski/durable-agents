# 5. Tools

> **On this page:** [Authoring a tool](#authoring-a-tool) · [How schemas are generated](#how-schemas-are-generated) · [Tool options](#tool-options) · [The tool registry](#the-tool-registry) · [Built-in filesystem tools](#built-in-filesystem-tools) · [Error handling](#error-handling)

Tools are the actions an agent can take. In `durable-agents` a tool is just an
`async` Python function decorated with `@tool`.

## Authoring a tool

```python
from durable_agents import tool

@tool
async def web_search(query: str) -> str:
    """Search the web for information about the given query."""
    # your real implementation here
    return f"Results for {query}: ..."
```

Two things happen on decoration:

1. The function's **docstring** becomes the tool description the model sees.
2. The function's **type hints** are converted into a JSON-schema `parameters`
   object describing its arguments.

Pass the decorated function to `create_durable_agent(tools=[...])`. Passing an
**undecorated** function raises `ValueError` — the agent needs the generated
schema.

> Tools must be `async`. They run inside a Temporal activity (`dispatch_tool`),
> so they may perform I/O freely — network calls, file access, database queries.

## How schemas are generated

The `@tool` decorator inspects the function signature and maps Python types to
JSON-schema types:

| Python type | JSON schema |
|---|---|
| `str` | `string` |
| `int` | `integer` |
| `float` | `number` |
| `bool` | `boolean` |
| `list` | `array` |
| `dict` | `object` |
| *anything else* | falls back to `string` |

Parameters **without a default value** are marked `required`. For example:

```python
@tool
async def fetch(url: str, retries: int = 3) -> str:
    """Fetch a URL."""
    ...
```

produces:

```json
{
  "type": "object",
  "properties": {
    "url": {"type": "string"},
    "retries": {"type": "integer"}
  },
  "required": ["url"]
}
```

Keep signatures simple and well-typed; the quality of the generated schema
directly affects how reliably the model calls the tool.

## Tool options

`@tool` accepts optional keyword arguments for per-tool execution tuning:

```python
@tool(timeout_seconds=30, max_retries=2)
async def slow_tool(url: str) -> str:
    """A tool that may take a while."""
    ...
```

| Option | Meaning |
|---|---|
| `timeout_seconds` | Activity `start_to_close` timeout for this tool's invocation. Defaults to 300 seconds when omitted. |
| `max_retries` | Maximum Temporal attempts for this tool's activity. Omitted means Temporal's default retry policy applies. |

These options are stored on the tool's `ToolEntry`, resolved when the item runs
(`execute_plan_item`), and carried back on the `ItemResult` so the workflow can
apply them **deterministically** when it dispatches the tool.

## The tool registry

When `@tool` runs, it registers a `ToolEntry` (name, callable, description,
parameters, options) into a process-local **`ToolRegistry`**. This registry is
the single source of truth the activities read at execution time — it is why
**tool schemas never travel over the wire** and why clients stay thin (see
[Core Concepts](03-core-concepts.md#the-agent-on-worker-model)).

The registry also exposes the tool schemas in OpenAI's `tools=` format via
`to_openai_tools()`, which the planner and execution activities use when calling
the model.

## Built-in filesystem tools

The framework ships ready-made filesystem tools you can drop into any agent:

```python
from durable_agents.tools.filesystem import (
    read_file, write_file, list_dir, search_files,
)

agent = create_durable_agent(
    model="openai:gpt-4o-mini",
    tools=[read_file, write_file, list_dir, search_files],
    task_queue="file-agent",
)
```

| Tool | Signature | Description |
|---|---|---|
| `read_file` | `read_file(path)` | Read UTF-8 text from a file. |
| `write_file` | `write_file(path, content)` | Write text to a file, creating parent directories. |
| `list_dir` | `list_dir(path)` | List directory entries (directories suffixed with `/`). |
| `search_files` | `search_files(directory, pattern)` | Recursive glob search for files. |

These power the [Code Archaeologist example](09-examples.md#example-03--code-archaeologist).

## Error handling

A tool that raises does **not** crash the agent. The `dispatch_tool` activity
catches the exception and returns an error string (e.g.
`ERROR calling tool 'read_file': FileNotFoundError: ...`). That string is fed
back into the loop as an observation, so the model can adjust — retry with a
different path, pick another tool, or report the problem. This is the
[semantic-fault retry layer](03-core-concepts.md#two-retry-layers) in action.

Next: [Sub-Agents](06-sub-agents.md).
