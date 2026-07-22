"""Analyzer protocol.

Every analyzer receives an :class:`AnalysisContext` and returns a
:class:`~verifact.models.Signal`. Analyzers must NEVER raise — they catch
their own errors and return a Signal with status=error, so one flaky
network call never sinks the whole report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..config import Settings
from ..models import Claim, ContentMeta, Signal


@dataclass
class AnalysisContext:
    """Everything an analyzer may need."""

    input_type: str  # url | text | image
    text: str = ""
    meta: ContentMeta = field(default_factory=ContentMeta)
    image_path: str | None = None
    claims: list[Claim] = field(default_factory=list)
    settings: Settings | None = None


@runtime_checkable
class Analyzer(Protocol):
    name: str
    title: str

    async def run(self, ctx: AnalysisContext) -> Signal: ...


def error_signal(name: str, title: str, exc: Exception, weight: float = 1.0) -> Signal:
    from ..models import SignalStatus

    return Signal(
        name=name,
        title=title,
        status=SignalStatus.ERROR,
        weight=weight,
        summary=f"Analyzer failed: {type(exc).__name__}: {exc}",
    )


def skipped_signal(name: str, title: str, reason: str, weight: float = 1.0) -> Signal:
    from ..models import SignalStatus

    return Signal(
        name=name, title=title, status=SignalStatus.SKIPPED, weight=weight, summary=reason
    )
