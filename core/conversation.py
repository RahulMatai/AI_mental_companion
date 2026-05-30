"""Conversation handler. Wraps the Groq client and holds the chat turn logic.

Decisions:
- Streaming responses so the UI feels alive instead of frozen.
- We inject WRAPUP_HINT after N user turns to encourage natural endings —
  prevents the infinite-chat trap where the AI never wraps up.
- Temperature is moderate (0.7): warm but not chaotic.
- Conversation history is stored client-side (in session state) and passed
  in full each turn. SQLite is the durable log, not the source of truth
  for the active conversation.
"""
import os
from typing import Iterator

from groq import Groq

from core.prompts import SYSTEM_PROMPT, WRAPUP_HINT
from utils.logger import get_logger

logger = get_logger(__name__)

# After this many user turns, nudge the model toward closing gracefully.
WRAPUP_AFTER_USER_TURNS = 6


def _client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file."
        )
    return Groq(api_key=api_key)


def _model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _build_messages(history: list[dict]) -> list[dict]:
    """Build the messages payload for the Groq API.

    history is a list of {role, content} dicts (user/assistant only).
    We prepend the system prompt and, when long, the wrap-up nudge.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_turns = sum(1 for m in history if m["role"] == "user")
    if user_turns >= WRAPUP_AFTER_USER_TURNS:
        messages.append({"role": "system", "content": WRAPUP_HINT})
        logger.debug("Injecting wrap-up hint at %d user turns", user_turns)

    messages.extend(history)
    return messages


def stream_reply(history: list[dict]) -> Iterator[str]:
    """Yield chunks of the assistant's response as they arrive.

    history must end with a user message.
    """
    if not history or history[-1]["role"] != "user":
        raise ValueError("History must end with a user message.")

    client = _client()
    messages = _build_messages(history)

    logger.info(
        "Streaming reply | model=%s | turns=%d", _model(), len(history)
    )

    stream = client.chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=0.7,
        max_tokens=180,  # Hard cap. The prompt demands 2-3 sentences. This enforces it.
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def summarize_session(history: list[dict]) -> str:
    """One-line summary of a closed session for the history view.

    Done as a separate, cheap call. Falls back to a generic line if it fails
    — never block the user.
    """
    if not history:
        return ""

    try:
        client = _client()
        transcript = "\n".join(
            f"{m['role']}: {m['content']}" for m in history if m["role"] != "system"
        )
        resp = client.chat.completions.create(
            model=_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize the following conversation in a single short "
                        "sentence (max 12 words), past tense, from the user's "
                        "perspective. No quotes, no preamble. Example: "
                        "'Talked about work stress, felt lighter after.'"
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            temperature=0.3,
            max_tokens=40,
        )
        summary = resp.choices[0].message.content.strip().strip('"')
        logger.info("Generated summary: %s", summary)
        return summary
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)
        return "A quiet check-in."
