"""Content-style signals: does the writing *behave* like reliable reporting?

Zero-key linguistic heuristics, individually weak but collectively useful:
sensational/clickbait phrasing, ALL-CAPS shouting, exclamation density,
missing attribution (no quotes / no named sources), urgency-to-share
pressure, and byline/date presence.

These are style signals, not truth signals — hence a modest weight and
capped confidence.
"""

from __future__ import annotations

import re
from importlib import resources

from ..models import Finding, Signal, SignalStatus
from .base import AnalysisContext, error_signal

NAME = "content_signals"
TITLE = "Writing-style signals"
WEIGHT = 1.5

_ATTRIBUTION_RE = re.compile(
    r"\baccording to\b|\bsaid\b|\btold\b|\bstated\b|\bspokesperson\b|\bin a statement\b"
    r"|\breported\b|\bconfirmed\b|\bannounced\b|\bper\b a\b",
    re.IGNORECASE,
)
_SHARE_PRESSURE_RE = re.compile(
    r"\bshare (this|before|now|widely)\b|\bretweet\b|\bforward (this|to)\b|\bspread the word\b"
    r"|\bmake this viral\b|\bcopy and paste\b",
    re.IGNORECASE,
)


def _load_terms() -> list[str]:
    txt = resources.files("verifact.data").joinpath("sensational_terms.txt").read_text()
    return [ln.strip().lower() for ln in txt.splitlines() if ln.strip() and not ln.startswith("#")]


class ContentSignalsAnalyzer:
    name = NAME
    title = TITLE

    async def run(self, ctx: AnalysisContext) -> Signal:
        try:
            return self._run(ctx)
        except Exception as exc:  # noqa: BLE001
            return error_signal(NAME, TITLE, exc, WEIGHT)

    def _run(self, ctx: AnalysisContext) -> Signal:
        text = ctx.text or ""
        title = ctx.meta.title or ""
        blob = f"{title}\n{text}"
        blob_l = blob.lower()
        words = blob.split()
        n_words = max(len(words), 1)

        findings: list[Finding] = []
        score = 70.0  # neutral-professional prior; deduct for red flags

        hits = [t for t in _load_terms() if t in blob_l]
        if hits:
            deduction = min(35, 8 * len(hits))
            score -= deduction
            findings.append(
                Finding(
                    label=f"Sensational/clickbait phrasing ({len(hits)} hit(s))",
                    detail=", ".join(f"“{h}”" for h in hits[:6]),
                    impact="negative",
                )
            )

        caps_words = [w for w in words if len(w) >= 4 and w.isupper() and w.isalpha()]
        caps_ratio = len(caps_words) / n_words
        if caps_ratio > 0.02:
            score -= 10
            findings.append(
                Finding(
                    label="Excessive ALL-CAPS",
                    detail=f"{len(caps_words)} shouted words (e.g. {', '.join(caps_words[:4])})",
                    impact="negative",
                )
            )

        exclam = blob.count("!")
        if exclam / n_words > 0.01 and exclam >= 3:
            score -= 8
            findings.append(
                Finding(
                    label="High exclamation density",
                    detail=f"{exclam} exclamation marks in {n_words} words.",
                    impact="negative",
                )
            )

        if _SHARE_PRESSURE_RE.search(blob):
            score -= 12
            findings.append(
                Finding(
                    label="Pressure to share/forward",
                    detail="Urging readers to spread content is a virality tactic, "
                    "not a journalism practice.",
                    impact="negative",
                )
            )

        if n_words > 120:
            if _ATTRIBUTION_RE.search(text):
                score += 8
                findings.append(
                    Finding(
                        label="Contains source attribution",
                        detail="Quotes/attributed statements present.",
                        impact="positive",
                    )
                )
            else:
                score -= 10
                findings.append(
                    Finding(
                        label="No visible attribution",
                        detail="Long piece with no 'according to…', quotes, or named sources.",
                        impact="negative",
                    )
                )

        if ctx.input_type == "url":
            if ctx.meta.author:
                score += 4
                findings.append(
                    Finding(label="Byline present", detail=ctx.meta.author, impact="positive")
                )
            else:
                findings.append(
                    Finding(
                        label="No byline detected",
                        detail="Reputable outlets usually name their reporters.",
                        impact="negative",
                    )
                )
                score -= 4
            if ctx.meta.published:
                findings.append(
                    Finding(
                        label="Publication date present",
                        detail=str(ctx.meta.published),
                        impact="positive",
                    )
                )
            else:
                score -= 3
                findings.append(
                    Finding(
                        label="No publication date detected",
                        detail="Undated articles resist verification and get endlessly recycled.",
                        impact="negative",
                    )
                )

        score = max(0.0, min(100.0, score))
        neg = sum(1 for f in findings if f.impact == "negative")
        summary = (
            "Writing style consistent with professional reporting."
            if neg == 0
            else f"{neg} style red flag(s) — patterns common in low-quality or viral content."
        )
        return Signal(
            name=NAME,
            title=TITLE,
            status=SignalStatus.OK,
            score=score,
            weight=WEIGHT,
            confidence=0.55,
            summary=summary,
            findings=findings,
        )
