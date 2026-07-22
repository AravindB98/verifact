"""Optional LLM layer — thin httpx clients, no vendor SDKs.

Used for claim extraction and per-claim reasoning when the user configures
``VERIFACT_ANTHROPIC_API_KEY`` or ``VERIFACT_OPENAI_API_KEY``. Everything in
VeriFact must work without this module ever being called.
"""

from __future__ import annotations

import json
import re

import httpx

from .config import Settings


class LLMError(Exception):
    pass


async def complete(settings: Settings, system: str, user: str, max_tokens: int = 1500) -> str:
    if settings.anthropic_api_key:
        return await _anthropic(settings, system, user, max_tokens)
    if settings.openai_api_key:
        return await _openai(settings, system, user, max_tokens)
    raise LLMError("No LLM API key configured")


async def _anthropic(settings: Settings, system: str, user: str, max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        if resp.status_code != 200:
            raise LLMError(f"Anthropic API {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
    return "".join(b.get("text", "") for b in data.get("content", []))


async def _openai(settings: Settings, system: str, user: str, max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        if resp.status_code != 200:
            raise LLMError(f"OpenAI API {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
    return data["choices"][0]["message"]["content"]


def extract_json_array(text: str) -> list:
    """Robustly pull the first JSON array out of an LLM response."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise LLMError("LLM response contained no JSON array")
    return json.loads(match.group(0))
