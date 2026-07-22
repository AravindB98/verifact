"""Score aggregation → verdict.

Weighted, confidence-modulated average over all OK signals that produced a
score. Signals with score=None (informational-only) are excluded. If fewer
than two scoring signals are available, VeriFact refuses to pick a band and
returns INSUFFICIENT — honesty over false precision.
"""

from __future__ import annotations

from .models import (
    VERDICT_LABELS,
    CredibilityReport,
    Signal,
    SignalStatus,
    Verdict,
)

MIN_SCORING_SIGNALS = 2


def aggregate(signals: list[Signal]) -> tuple[float | None, Verdict, float]:
    scored = [s for s in signals if s.status == SignalStatus.OK and s.score is not None and s.weight > 0]
    if len(scored) < MIN_SCORING_SIGNALS:
        return None, Verdict.INSUFFICIENT, 0.0

    total_w = sum(s.weight * s.confidence for s in scored)
    if total_w <= 0:
        return None, Verdict.INSUFFICIENT, 0.0
    score = sum(s.score * s.weight * s.confidence for s in scored) / total_w

    # Hard override: a known-satire or fact-checked-false source shouldn't be
    # averaged up by good writing style.
    for s in scored:
        if s.name in ("source_reputation", "factcheck_db") and s.score <= 15 and s.confidence >= 0.75:
            score = min(score, 30.0)

    confidence = min(0.95, sum(s.confidence for s in scored) / len(scored) * (len(scored) / 5 + 0.4))
    verdict = (
        Verdict.HIGH
        if score >= 75
        else Verdict.MODERATE
        if score >= 55
        else Verdict.LOW
        if score >= 35
        else Verdict.VERY_LOW
    )
    return round(score, 1), verdict, round(confidence, 2)


def summarize(report: CredibilityReport) -> str:
    ok = [s for s in report.signals if s.status == SignalStatus.OK]
    neg = [f for s in ok for f in s.findings if f.impact == "negative"]
    pos = [f for s in ok for f in s.findings if f.impact == "positive"]
    if report.verdict == Verdict.INSUFFICIENT:
        return (
            "Not enough independent signals to score this content. "
            "Check the individual findings below and verify manually."
        )
    parts = [f"{VERDICT_LABELS[report.verdict]} ({report.score}/100)."]
    if pos:
        parts.append(f"{len(pos)} positive indicator(s).")
    if neg:
        parts.append(f"{len(neg)} red flag(s).")
    top = max(ok, key=lambda s: (s.weight * s.confidence) if s.score is not None else 0, default=None)
    if top and top.summary:
        parts.append(f"Strongest signal — {top.title.lower()}: {top.summary}")
    return " ".join(parts)


def finalize(report: CredibilityReport) -> CredibilityReport:
    score, verdict, confidence = aggregate(report.signals)
    report.score = score
    report.verdict = verdict
    report.verdict_label = VERDICT_LABELS[verdict]
    report.confidence = confidence
    report.analyzers_run = sum(1 for s in report.signals if s.status == SignalStatus.OK)
    report.analyzers_skipped = sum(1 for s in report.signals if s.status == SignalStatus.SKIPPED)
    report.summary = summarize(report)
    return report
