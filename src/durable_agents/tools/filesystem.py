"""Built-in filesystem tools for durable-agents.

These async functions are decorated with ``@tool`` and are automatically
registered in the global tool registry on import.  Use them as tools when
creating an agent::

    from durable_agents.tools.filesystem import read_file, write_file, list_dir, search_files

    agent = create_durable_agent(
        model="openai:gpt-4o-mini",
        tools=[read_file, write_file, list_dir, search_files],
        task_queue="my-agent",
    )

All functions run inside Temporal Activities and are therefore subject to the
normal activity retry / timeout rules.  ``write_file`` is idempotent in the
sense that retrying an activity after a crash will simply overwrite the file
with the same content — downstream consumers should treat the file as
eventually-consistent with the activity result.
"""
from __future__ import annotations

import pathlib

from durable_agents.tools.decorators import tool


@tool
async def read_file(path: str) -> str:
    """Read and return the UTF-8 text content of the file at *path*.

    Raises ``FileNotFoundError`` if the file does not exist.
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {path!r}")
    return p.read_text(encoding="utf-8")


@tool
async def write_file(path: str, content: str) -> str:
    """Write *content* to the file at *path*, creating parent directories as needed.

    Returns a confirmation message with the number of bytes written.
    Overwrites the file if it already exists.
    """
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written {len(content.encode())} bytes to {path!r}"


@tool
async def list_dir(path: str) -> str:
    """Return a newline-separated listing of entries in directory *path*.

    Directory names are suffixed with ``/``.
    Raises ``NotADirectoryError`` if *path* does not exist or is not a directory.
    """
    p = pathlib.Path(path)
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {path!r}")
    entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name))
    lines = [f"{e.name}/" if e.is_dir() else e.name for e in entries]
    return "\n".join(lines)


@tool
async def search_files(directory: str, pattern: str) -> str:
    """Recursively search *directory* for files matching the glob *pattern*.

    Returns a newline-separated list of matching paths relative to *directory*.
    Returns an empty string when no files match (no error raised).
    """
    base = pathlib.Path(directory)
    matches = sorted(base.rglob(pattern))
    return "\n".join(str(m.relative_to(base)) for m in matches if m.is_file())
