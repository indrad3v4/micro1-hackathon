"""LLM client for Creative Court agents.

Pluggable backend: OpenAI-compatible API (CometAPI etc.) when configured,
deterministic heuristic fallback when not — so the harness always runs.

Supported environment variables:
    COMETAPI_KEY   - Primary API key (CometAPI compatible)
    OPENROUTER_API_KEY - Fallback if COMETAPI_KEY is unset
    LLM_BASE_URL   - API base URL (default: https://api.cometapi.com/v1)
    LLM_MODEL      - Model to use (default: deepseek-v4-flash-vision-exp)
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Optional


# ИКРА compass of frames — where creative tasks are already solved
FRAMES = [
    "artistic",      # art/aesthetic expression
    "social",        # community/relationship
    "professional",  # craft/expertise
    "historical",    # tradition/heritage
    "ritual",        # habit/ceremony/daily rhythm
    "natural",       # nature/organic systems
]


def _resolve_key() -> str | None:
    """Return the first available API key from known env vars."""
    return (os.environ.get("COMETAPI_KEY") or
            os.environ.get("OPENROUTER_API_KEY") or
            os.environ.get("LLM_API_KEY"))


def _resolve_base() -> str:
    """Return the API base URL, with provider-specific defaults."""
    key = _resolve_key()
    url = os.environ.get("LLM_BASE_URL", "")
    if url:
        return url
    if key and ("sk-or-" in (key[:50] or "")):
        return "https://openrouter.ai/api/v1"
    return "https://api.cometapi.com/v1"


def _resolve_model() -> str:
    """Return model name, falling back to the CometAPI-native default."""
    return (os.environ.get("LLM_MODEL") or
            "deepseek-v4-flash")


class LLMClient:
    """Minimal OpenAI-compatible chat client with heuristic fallback.

    Reads COMETAPI_KEY / OPENROUTER_API_KEY / LLM_API_KEY; detects
    provider and sets the right base URL automatically. If no key, calls
    to :meth:`chat` raise ``RuntimeError`` so callers can fall back
    to determinism.
    """

    def __init__(self, model: Optional[str] = None):
        self.key = _resolve_key()
        self.base = _resolve_base()
        self.model = model or _resolve_model()

    @property
    def available(self) -> bool:
        return bool(self.key)

    def chat(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        if not self.available:
            raise RuntimeError("no LLM key configured — use heuristic fallback")

        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }

        req = urllib.request.Request(f"{self.base}/chat/completions", data=body, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise RuntimeError(f"LLM API call failed ({exc})") from exc


def load_prompt(path: str) -> str:
    """Load a prompt template from disk, returning empty string on failure."""
    try:
        return open(path, encoding="utf-8").read().strip()
    except (OSError, IOError):
        return ""


def heuristic_directions(brief, frames=FRAMES) -> list[dict]:
    """Deterministic offline fallback: one direction per frame."""
    out = []
    for i, frame in enumerate(frames):
        out.append({
            "frame": frame,
            "name": f"{frame.capitalize()} angle",
            "concept": (f"Turn «{brief.title}» into an experience framed as {frame} "
                        f"expression for {brief.audience or 'the target audience'}."),
            "rationale": (f"The {frame} frame reframes the core value so the audience "
                          f"sees it through a familiar lens."),
            "risks": ["needs validation with real users"] if i % 2 == 0 else [],
        })
    return out
