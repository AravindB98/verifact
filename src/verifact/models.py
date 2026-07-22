"""Pydantic models for VeriFact analysis reports.

The core contract of VeriFact: every analyzer produces a :class:`Signal`,
and the pipeline aggregates signals into a :class:`CredibilityReport`.
VeriFact never outputs a binary "true/false" — it outputs *evidence*,
per-signal scores, and an overall credibility band with confidence.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SignalStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"  # analyzer not applicable / no key configured
    ERROR = "error"


class Verdict(str, Enum):
    HIGH = "high_credibility"
    MODERATE = "moderate_credibility"
    LOW = "low_credibility"
    VERY_LOW = "very_low_credibility"
    INSUFFICIENT = "insufficient_evidence"


VERDICT_LABELS: dict[Verdict, str] = {
    Verdict.HIGH: "High credibility",
    Verdict.MODERATE: "Moderate credibility",
    Verdict.LOW: "Low credibility",
    Verdict.VERY_LOW: "Very low credibility",
    Verdict.INSUFFICIENT: "Insufficient evidence",
}


class Finding(BaseModel):
    """A single piece of evidence produced by an analyzer."""

    label: str
    detail: str = ""
    impact: str = Field(
        default="neutral",
        description="One of: positive, negative, neutral, informational",
    )
    evidence_url: str | None = None


class Signal(BaseModel):
    """Result of one analyzer."""

    name: str
    title: str
    status: SignalStatus = SignalStatus.OK
    score: float | None = Field(
        default=None, ge=0, le=100, description="0 (not credible) – 100 (credible)"
    )
    weight: float = Field(default=1.0, ge=0)
    confidence: float = Field(default=0.5, ge=0, le=1)
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    raw: dict[str, Any] | None = Field(
        default=None, description="Analyzer-specific raw payload (kept small)"
    )


class Claim(BaseModel):
    """A discrete factual claim extracted from the content."""

    text: str
    checkworthy: bool = True
    assessment: str | None = Field(
        default=None,
        description="corroborated | contradicted | disputed | unverified",
    )
    notes: str = ""
    sources: list[str] = Field(default_factory=list)


class ContentMeta(BaseModel):
    url: str | None = None
    domain: str | None = None
    title: str | None = None
    author: str | None = None
    published: str | None = None
    word_count: int = 0
    language: str | None = None
    excerpt: str = ""


class CredibilityReport(BaseModel):
    """Aggregated verification report."""

    input_type: str = "url"  # url | text | image
    meta: ContentMeta = Field(default_factory=ContentMeta)
    score: float | None = None
    verdict: Verdict = Verdict.INSUFFICIENT
    verdict_label: str = VERDICT_LABELS[Verdict.INSUFFICIENT]
    confidence: float = 0.0
    summary: str = ""
    signals: list[Signal] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    disclaimer: str = (
        "VeriFact estimates credibility from observable signals. It does not "
        "determine absolute truth. Always check the cited evidence yourself, "
        "especially for breaking news where corroboration may not exist yet."
    )
    engine_version: str = "0.1.0"
    analyzers_run: int = 0
    analyzers_skipped: int = 0
