"""Code Archaeologist — Client entry point.

Submits the analysis task to the ``code-archaeologist`` orchestrator and
prints the final synthesised result.

Usage::

    # Requires worker.py and a Temporal server to be running first.
    uv run python examples/03_code_archaeologist/client.py

    # Optionally specify a custom path to the legacy code directory:
    uv run python examples/03_code_archaeologist/client.py /path/to/legacy

The bundled ``legacy/`` directory is treated as a read-only **fixture**: the
client copies it into a sibling ``_work/`` directory and points the agents
there, so repeated demo runs never mutate the original sample code while the
modernised output stays easy to find next to the example.
"""
from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

from durable_agents import DurableAgentClient

_DEFAULT_LEGACY_DIR = str(Path(__file__).parent / "legacy")
_WORK_ROOT = Path(__file__).parent / "_work"


def _make_work_copy(source_dir: str) -> str:
    """Copy *source_dir* into a fresh ``_work/`` directory and return its path.

    The agents read and rewrite files in this working copy, leaving the
    original fixture untouched so the demo is fully repeatable. ``_work/`` sits
    next to this script (and is git-ignored) so the modernised artifacts are
    easy to inspect after a run.
    """
    src = Path(source_dir)
    dest = _WORK_ROOT / src.name
    if _WORK_ROOT.exists():
        shutil.rmtree(_WORK_ROOT)
    shutil.copytree(src, dest)
    return str(dest)


async def main(source_dir: str) -> None:
    work_dir = _make_work_copy(source_dir)

    task = (
        f"Analyse and modernise the legacy Python code in the directory: {work_dir}\n\n"
        "1. First, use the archaeologist to discover and analyse all Python files.\n"
        "2. Then use the modernizer to rewrite the files with modern idioms.\n"
        "3. Finally use the documenter to add docstrings and a README.\n"
        "Provide a summary of all changes made."
    )

    print("Submitting task to 'code-archaeologist' task queue …")
    print(f"Fixture (read-only): {source_dir}")
    print(f"Working copy (agents write here): {work_dir}")
    print("Workflow visible at http://localhost:8233\n")

    client = DurableAgentClient(task_queue="code-archaeologist")
    result = await client.run(task)

    print("=== Result ===")
    print(result)
    print(f"\nModernised artifacts are in: {work_dir}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_LEGACY_DIR
    asyncio.run(main(target))
