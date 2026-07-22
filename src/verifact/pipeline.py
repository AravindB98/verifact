"""Pipeline orchestrator: fetch → extract claims → run analyzers → aggregate."""

from __future__ import annotations

import asyncio

from .analyzers.base import AnalysisContext
from .analyzers.claims import ClaimExtractionAnalyzer
from .analyzers.content_signals import ContentSignalsAnalyzer
from .analyzers.corroboration import CorroborationAnalyzer
from .analyzers.factcheck import FactCheckDBAnalyzer
from .analyzers.media import MediaProvenanceAnalyzer
from .analyzers.source_reputation import SourceReputationAnalyzer
from .config import get_settings
from .extract import fetch_url, meta_for_text
from .models import CredibilityReport, Finding, Signal, SignalStatus
from .scoring import finalize
from .social import detect_platform, fetch_social


async def analyze_url(url: str) -> CredibilityReport:
    if detect_platform(url):
        return await analyze_social(url)
    text, meta = await fetch_url(url)
    ctx = AnalysisContext(input_type="url", text=text, meta=meta, settings=get_settings())
    return await _run(ctx)


async def analyze_social(url: str) -> CredibilityReport:
    """Analyze an X / Instagram / Facebook / LinkedIn post from its share link."""
    text, meta, post = await fetch_social(url)
    ctx = AnalysisContext(input_type="social", text=text, meta=meta, settings=get_settings())
    report = await _run(ctx)

    findings = [
        Finding(label="Platform", detail=post.platform, impact="informational"),
    ]
    if post.author:
        findings.append(Finding(label="Author", detail=str(post.author), impact="informational"))
    followers = post.extras.get("author_followers")
    if followers is not None:
        findings.append(
            Finding(
                label="Author followers",
                detail=f"{followers:,}",
                impact="informational",
            )
        )
    if post.partial:
        findings.append(
            Finding(
                label="Partial extraction",
                detail="Only the link-preview (OpenGraph) text was publicly available — the "
                "post may be longer. Paste the full text for a deeper check.",
                impact="informational",
            )
        )
    report.signals.insert(
        0,
        Signal(
            name="social_context",
            title="Social post context",
            status=SignalStatus.OK,
            score=None,  # informational — a post's platform is not evidence either way
            weight=0,
            confidence=0.9,
            summary=(
                f"{post.platform} post"
                + (f" by {post.author}" if post.author else "")
                + (" (partial preview text only)" if post.partial else "")
                + " — credibility rests on the claims and corroboration below, not the platform."
            ),
            findings=findings,
        ),
    )
    return report


async def analyze_text(text: str) -> CredibilityReport:
    ctx = AnalysisContext(
        input_type="text", text=text, meta=meta_for_text(text), settings=get_settings()
    )
    return await _run(ctx)


async def analyze_image(image_path: str, caption: str = "") -> CredibilityReport:
    ctx = AnalysisContext(
        input_type="image",
        text=caption,
        meta=meta_for_text(caption or ""),
        image_path=image_path,
        settings=get_settings(),
    )
    return await _run(ctx)


async def _run(ctx: AnalysisContext) -> CredibilityReport:
    report = CredibilityReport(input_type=ctx.input_type, meta=ctx.meta)

    # Stage 1 — claim extraction feeds downstream analyzers.
    claims_signal = await ClaimExtractionAnalyzer().run(ctx)

    # Stage 2 — independent analyzers run concurrently.
    stage2 = [
        SourceReputationAnalyzer(),
        ContentSignalsAnalyzer(),
        FactCheckDBAnalyzer(),
        CorroborationAnalyzer(),
        MediaProvenanceAnalyzer(),
    ]
    results = await asyncio.gather(*(a.run(ctx) for a in stage2))

    report.claims = ctx.claims
    report.signals = [claims_signal, *results]
    from . import __version__

    report.engine_version = __version__
    return finalize(report)
