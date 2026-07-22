"""The Narrator (Gilded Saga §5): the ONLY model call site, at the display
boundary. render() takes a composed TurnReport plus the Director and returns a
TurnReport - it may rewrite prose but never touches sim state. Templated is the
deterministic default and guaranteed fallback; LLM is opt-in."""

import json
import os
import urllib.request
from typing import Protocol

from gilded.papers import TurnReport


class Narrator(Protocol):
    def render(self, report: TurnReport, director, game) -> TurnReport: ...


class NarratorTemplated:
    """Identity: today's exact broadsheet. Used in every automated test."""

    def render(self, report: TurnReport, director, game) -> TurnReport:
        return report


def active_context(director):
    """Deterministic foreshadow/era/rival context for a narration prompt."""
    lines = []
    for bid in getattr(director, "active", []):
        b = director.beats.get(bid)
        if b is not None and b.foreshadow:
            lines.append(b.foreshadow)
    return lines


MODEL_URL = os.environ.get("GILDED_MODEL_URL", "http://127.0.0.1:11434/v1/chat/completions")
MODEL_NAME = os.environ.get("GILDED_MODEL_NAME", "qwen3.6")
NARRATE_TIMEOUT = float(os.environ.get("GILDED_NARRATE_TIMEOUT", "30"))


def _post_chat(messages, timeout=NARRATE_TIMEOUT):
    body = json.dumps({
        "model": MODEL_NAME, "messages": messages, "temperature": 0.7,
        "max_tokens": 220, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    req = urllib.request.Request(MODEL_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


class NarratorLLM:
    """Local Qwen3.6 narration. On any failure, returns the report unchanged."""

    def __init__(self, check: bool = True):
        if check:
            _post_chat([{"role": "user", "content": "ok"}], timeout=3)  # warmup/probe

    def render(self, report: TurnReport, director, game) -> TurnReport:
        if not report.gazette:
            return report
        context = active_context(director)
        prompt = (
            "You are the chronicler of a dynastic saga in an industrial age. "
            "In one vivid paragraph, weave this turn's events into the ongoing story. "
            "Standing threads: " + ("; ".join(context) if context else "none") + ". "
            "This turn's dispatches:\n- " + "\n- ".join(report.gazette[:10])
        )
        try:
            prose = _post_chat([{"role": "user", "content": prompt}])
        except Exception:
            return report
        if not prose:
            return report
        return TurnReport(report.turn, report.year, [prose] + report.gazette,
                          report.ledger, report.letters)


def select_narrator() -> Narrator:
    """App/console factory: LLM by default, templated when disabled."""
    if os.environ.get("GILDED_NARRATE", "1") == "0":
        return NarratorTemplated()
    try:
        return NarratorLLM()
    except Exception:
        return NarratorTemplated()
