from __future__ import annotations

from openai import AsyncOpenAI
from temporalio import activity

from durable_agents.config import LLM_MAX_TOKENS, OPENAI_API_KEY, OPENAI_MODEL

# Module-level client — created outside workflow code (determinism safe).
_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Number of recent messages to keep verbatim after summarisation.
_KEEP_RECENT = 4


@activity.defn
async def summarise_context(history: list[dict]) -> list[dict]:
    """Compress message history by summarising the middle section.

    Keeps the first message (system prompt, if any) and the last
    ``_KEEP_RECENT`` messages intact.  The middle section is replaced with a
    single assistant message containing an LLM-generated summary.

    Returns the compressed history as a list of serialised Message dicts.
    """
    if len(history) <= _KEEP_RECENT + 1:
        # Nothing to compress.
        return history

    first = history[:1]  # system message (or first user message)
    middle = history[1:-_KEEP_RECENT]
    recent = history[-_KEEP_RECENT:]

    # Build a condensed view of the middle section for the LLM.
    middle_text = "\n".join(
        f"[{m['role']}]: {m['content']}" for m in middle
    )

    summary_response = await _client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarise the following conversation excerpt concisely, "
                    "preserving all tool calls, results, and key facts."
                ),
            },
            {"role": "user", "content": middle_text},
        ],
    )

    summary_content = summary_response.choices[0].message.content or "(summary unavailable)"
    summary_message = {"role": "assistant", "content": f"[Context summary]\n{summary_content}"}

    return first + [summary_message] + recent
