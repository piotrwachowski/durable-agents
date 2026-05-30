from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def skill(cls: type) -> type:
    """Class decorator that marks a class as a reusable agent skill.

    A skill class must declare two class attributes:

    - ``tools``: a list of functions decorated with ``@tool``
    - ``system_prompt``: a string prompt fragment to append to the agent's
      base system prompt

    The decorator sets a ``__is_skill__`` marker on the class so that
    ``create_durable_agent`` can validate inputs at registration time.

    Skills are **not** registered globally on decoration; they are only
    activated when passed to ``create_durable_agent(skills=[...])`` on the
    worker side.
    """
    cls.__is_skill__ = True  # type: ignore[attr-defined]
    return cls
