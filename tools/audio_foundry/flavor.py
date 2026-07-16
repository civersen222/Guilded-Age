"""Optional LLM flavor text via Lemonade. Returns None when unavailable."""
from __future__ import annotations
from .lemonade import LemonadeHost

_PROMPT = (
    "Write a single vivid sentence of chronicle flavor for this game event. "
    "Reply with only the sentence, no preamble.\nEvent: {event}"
)


def author_line(event_desc: str, host: LemonadeHost | None = None) -> str | None:
    """Return one line of flavor text for an event, or None if generation fails.

    Never raises. When the Lemonade host is down (or returns nothing) the caller
    should fall back to the event's own static description.
    """
    host = host or LemonadeHost()
    if not event_desc.strip():
        return None
    text = host.generate_text(_PROMPT.format(event=event_desc.strip()))
    if not text:
        return None
    return text.strip().splitlines()[0].strip() or None
