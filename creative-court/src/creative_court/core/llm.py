"""LLM client for Creative Court agents.

Pluggable backend: OpenAI-compatible API (CometAPI etc.) when configured,
deterministic heuristic fallback when not — so the harness always runs.
"""
from __future__ import annotations

import json
import os
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


class LLMClient:
    """Minimal OpenAI-compatible chat client with heuristic fallback.

    Reads COMETAPI_KEY / LLM_API_KEY, base URL from LLM_BASE_URL
    (default https://api.cometapi.com/v1). If no key, generate_directions
    uses a deterministic template so the pipeline runs offline.
    """

    def __init__(self, model: Optional[str] = None):
        self.key = os.environ.get("COMETAPI_KEY") or os.environ.get("LLM_API_KEY")
        self.base = os.environ.get("LLM_BASE_URL", "https://api.cometapi.com/v1")
        self.model = model or os.environ.get("LLM_MODEL", "deepseek-v4-flash-vision-exp")

    @property
    def available(self) -> bool:
        return bool(self.key)

    def chat(self, system: str, user: str, max_tokens: int = 2048) -> str:
        if not self.available:
            raise RuntimeError("no LLM key configured — use heuristic fallback")
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()


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
