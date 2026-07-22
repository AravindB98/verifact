"""Claim extraction: identify the discrete, check-worthy factual claims.

Two modes:
- **LLM mode** (key configured): extracts precise claims and flags which are
  check-worthy, with brief reasoning about internal consistency.
- **Heuristic mode** (zero-key): scores sentences for "claim-likeness" —
  numbers, percentages, dates, named entities, causal/reporting verbs —
  and surfaces the top candidates.

This analyzer feeds ``ctx.claims`` for the fact-check and corroboration
analyzers downstream. It contributes only a light score itself (a text with
zero verifiable claims is unfalsifiable — which is itself a signal).
"""

from __future__ import annotations

import re

from .. import llm
from ..models import Claim, Finding, Signal, SignalStatus
from .base import AnalysisContext, error_signal

NAME = "claims"
TITLE = "Claim extraction"
WEIGHT = 1.0

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'])")
_NUMBERY = re.compile(r"\d")
_PERCENT = re.compile(r"\d+(\.\d+)?\s?(%|percent|per cent)", re.IGNORECASE)
_ENTITY = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
_REPORTING = re.compile(
    r"\b(said|announced|confirmed|reported|found|shows?|proves?|revealed|according to|"
    r"causes?|leads? to|results? in|kills?|cures?|prevents?|increases?|decreases?|"
    r"banned|approved|signed|launched|died|arrested|elected|won|lost)\b",
    re.IGNORECASE,
)
_HEDGE = re.compile(
    r"\b(may|might|could|reportedly|allegedly|rumou?red|some say|sources say|it is said)\b",
    re.IGNORECASE,
)

LLM_SYSTEM = """You are a claim-extraction engine inside VeriFact, an open-source \
credibility tool. Extract the discrete factual claims from the text. Return ONLY a JSON \
array; each element: {"text": "<claim restated atomically>", "checkworthy": true|false, \
"notes": "<≤20 words: why it matters / internal red flags>"}. Check-worthy = specific, \
falsifiable, consequential. Max %d claims. No commentary outside JSON."""


def heuristic_claims(text: str, max_claims: int) -> list[Claim]:
    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if 40 <= len(s.strip()) <= 350]
    scored: list[tuple[float, str]] = []
    for s in sentences:
        pts = 0.0
        if _NUMBERY.search(s):
            pts += 1.5
        if _PERCENT.search(s):
            pts += 1.5
        if _ENTITY.search(s):
            pts += 1.0
        if _REPORTING.search(s):
            pts += 1.5
        if _HEDGE.search(s):
            pts -= 0.5
        if s.endswith("?"):
            pts -= 2.0
        if pts >= 2.5:
            scored.append((pts, s))
    scored.sort(key=lambda t: -t[0])
    return [
        Claim(text=s, checkworthy=True, notes="heuristic extraction")
        for _, s in scored[:max_claims]
    ]


class ClaimExtractionAnalyzer:
    name = NAME
    title = TITLE

    async def run(self, ctx: AnalysisContext) -> Signal:
        try:
            return await self._run(ctx)
        except Exception as exc:  # noqa: BLE001
            return error_signal(NAME, TITLE, exc, WEIGHT)

    async def _run(self, ctx: AnalysisContext) -> Signal:
        settings = ctx.settings
        max_claims = settings.max_claims if settings else 8
        text = (ctx.text or "")[:12000]
        if len(text.split()) < 15:
            return Signal(
                name=NAME,
                title=TITLE,
                status=SignalStatus.OK,
                score=None,
                weight=0,
                confidence=0.3,
                summary="Text too short for claim extraction.",
            )

        mode = "heuristic"
        claims: list[Claim] = []
        if settings and settings.has_llm:
            try:
                raw = await llm.complete(settings, LLM_SYSTEM % max_claims, text)
                items = llm.extract_json_array(raw)
                claims = [
                    Claim(
                        text=str(it.get("text", ""))[:400],
                        checkworthy=bool(it.get("checkworthy", True)),
                        notes=str(it.get("notes", ""))[:200],
                    )
                    for it in items
                    if it.get("text")
                ][:max_claims]
                mode = "llm"
            except Exception:  # noqa: BLE001 — fall back, never fail
                claims = []
        if not claims:
            claims = heuristic_claims(text, max_claims)
            mode = "heuristic" if mode == "heuristic" else "heuristic (LLM fallback)"

        ctx.claims = claims  # feed downstream analyzers

        findings = [
            Finding(
                label=f"Claim {i + 1}",
                detail=c.text,
                impact="informational",
            )
            for i, c in enumerate(claims)
        ]

        # Unfalsifiable content is a mild red flag; claim-rich content is checkable.
        if claims:
            score, summary = 60.0, (
                f"Extracted {len(claims)} check-worthy claim(s) ({mode} mode) — "
                "see fact-check & corroboration signals for how they hold up."
            )
        else:
            score, summary = 45.0, (
                "No concrete, falsifiable claims found — content is opinion, vibe, or "
                "too vague to verify (unfalsifiability is itself a caution sign)."
            )

        return Signal(
            name=NAME,
            title=TITLE,
            status=SignalStatus.OK,
            score=score,
            weight=WEIGHT,
            confidence=0.5 if mode.startswith("heuristic") else 0.7,
            summary=summary,
            findings=findings,
            raw={"mode": mode, "count": len(claims)},
        )
