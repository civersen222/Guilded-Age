"""Lemonade runtime host adapter. Probe never raises; Mode B is always optional."""
from __future__ import annotations
import json
import urllib.request
from dataclasses import dataclass


@dataclass
class LemonadeHost:
    base_url: str = "http://localhost:8000"
    timeout: float = 2.0

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path

    def available(self) -> bool:
        """True if the host answers /health with a 2xx. Never raises."""
        try:
            req = urllib.request.Request(self._url("/health"), method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

    def generate_text(self, prompt: str, *, model: str = "default",
                      max_tokens: int = 256) -> str | None:
        """Call the OpenAI-compatible chat endpoint. Returns None on any failure."""
        try:
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }).encode("utf-8")
            req = urllib.request.Request(
                self._url("/v1/chat/completions"),
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except Exception:
            return None
