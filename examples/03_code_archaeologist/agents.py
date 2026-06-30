"""Code Archaeologist — agent definitions.

Four agents are defined here and imported by both worker.py and client.py:

- ``archaeologist_agent``  — reads legacy code and produces a findings report
- ``modernizer_agent``     — rewrites files to use modern Python idioms
- ``documenter_agent``     — adds docstrings and a module-level README
- ``orchestrator_agent``   — plans the full sequence and delegates to the others

Task queues:
    code-archaeologist  (orchestrator)
    archaeologist-agent
    modernizer-agent
    documenter-agent
"""
from __future__ import annotations

import os

from durable_agents import create_durable_agent
from durable_agents.tools.filesystem import list_dir, read_file, search_files, write_file

# Model for every agent below. Reads OPENAI_MODEL from the environment so the
# example works against OpenAI or a local server (Ollama/vLLM) without edits;
# the "openai:" provider prefix is added if missing. See docs/12-local-models.md.
_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
if not _MODEL.startswith("openai:"):
    _MODEL = f"openai:{_MODEL}"

# ── Sub-agents ────────────────────────────────────────────────────────────────

archaeologist_agent = create_durable_agent(
    model=_MODEL,
    tools=[read_file, search_files, list_dir],
    system_prompt=(
        "You are a Code Archaeologist. Your job is to read legacy Python source files "
        "and produce a detailed findings report that lists:\n"
        "  1. Each file you examined (by full path)\n"
        "  2. The specific code quality issues found (missing type hints, old-style "
        "string formatting, global mutable state, missing docstrings, etc.)\n"
        "  3. Concrete recommendations for each file\n\n"
        "Use search_files to discover Python files in the target directory, then "
        "use read_file to read each one. Write a thorough findings report that "
        "explicitly lists every file path you examined and its specific issues, "
        "so a downstream agent can act on it without re-reading the code."
    ),
    task_queue="archaeologist-agent",
    max_steps=10,
)

modernizer_agent = create_durable_agent(
    model=_MODEL,
    tools=[read_file, write_file],
    system_prompt=(
        "You are a Python Modernizer. Your job is to rewrite legacy Python files "
        "to use modern idioms:\n"
        "  - Add type annotations to all function signatures and variables\n"
        "  - Replace %-style string formatting with f-strings\n"
        "  - Replace global mutable state with function parameters or return values\n"
        "  - Use pathlib.Path instead of os.path / open()\n"
        "  - Use context managers (with statements) for file I/O\n\n"
        "Use read_file to read the original file, then write_file to save the "
        "modernized version in place (same path). Preserve all existing functionality."
    ),
    task_queue="modernizer-agent",
    max_steps=15,
)

documenter_agent = create_durable_agent(
    model=_MODEL,
    tools=[read_file, write_file],
    system_prompt=(
        "You are a Python Documenter. Your job is to add comprehensive documentation "
        "to already-modernized Python source files:\n"
        "  - Add a module-level docstring explaining the module's purpose\n"
        "  - Add Google-style docstrings to every public function and class\n"
        "  - Include Args, Returns, and Raises sections in each docstring\n"
        "  - Create a README.md in the same directory summarising the module\n\n"
        "Use read_file to read each file, then write_file to save the documented "
        "version. Also write_file to create the README.md."
    ),
    task_queue="documenter-agent",
    max_steps=15,
)

# ── Orchestrator ─────────────────────────────────────────────────────────────

orchestrator_agent = create_durable_agent(
    model=_MODEL,
    tools=[],
    sub_agents={
        "archaeologist": archaeologist_agent,
        "modernizer": modernizer_agent,
        "documenter": documenter_agent,
    },
    system_prompt=(
        "You are the Code Archaeologist Orchestrator. You coordinate a three-phase "
        "legacy code modernisation pipeline by delegating to specialised sub-agents.\n\n"
        "Phase 1 — Archaeology: Delegate to 'archaeologist' to analyse the legacy code "
        "and produce a findings report. Ask the archaeologist to search for Python files "
        "under the 'legacy/' directory relative to the path provided in the task, read "
        "each file, and return a findings report listing every file path and its issues.\n\n"
        "Phase 2 — Modernisation: After receiving the archaeologist's findings, delegate "
        "to 'modernizer' with explicit file paths from the findings report. Ask it to "
        "modernize each file in place.\n\n"
        "Phase 3 — Documentation: Delegate to 'documenter' with the same file paths. "
        "Ask it to add docstrings and create a README.md.\n\n"
        "Create a plan with exactly three delegate items (one per phase). All plan items "
        "must have type='delegate'. Do not use tools directly."
    ),
    task_queue="code-archaeologist",
    max_steps=20,
)
