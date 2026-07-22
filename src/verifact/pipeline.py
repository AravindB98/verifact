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
from .models import CredibilityReport
from .scoring import finalize


async def analyze_url(url: str) -> CredibilityReport:
    text, meta = await fetch_url(url)
    ctx = AnalysisContext(input_type="url", text=text, meta=meta, settings=get_settings())
    return await _run(ctx)


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
    return finalize(report)
