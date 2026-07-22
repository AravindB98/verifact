"""Fact-check database lookup via Google Fact Check Tools (ClaimReview).

Searches the global ClaimReview corpus (Snopes, PolitiFact, AFP, AltNews,
BOOM, Full Fact, …) for existing fact-checks matching the article's claims.

Works with a free Google API key (``VERIFACT_GOOGLE_FACTCHECK_API_KEY``).
Without a key the analyzer is skipped — transparently reported, never faked.
"""

from __future__ import annotations

import httpx

from ..models import Finding, Signal, SignalStatus
from .base import AnalysisContext, error_signal, skipped_signal

NAME = "factcheck_db"
TITLE = "Fact-check databases"
WEIGHT = 2.0

API = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

_FALSE_WORDS = ("false", "fake", "incorrect", "misleading", "pants on fire", "debunk", "hoax")
_TRUE_WORDS = ("true", "correct", "accurate", "legit")


def rating_polarity(rating: str) -> int:
    r = rating.lower()
    if any(w in r for w in _FALSE_WORDS):
        return -1
    if any(w in r for w in _TRUE_WORDS):
        return 1
    return 0


class FactCheckDBAnalyzer:
    name = NAME
    title = TITLE

    async def run(self, ctx: AnalysisContext) -> Signal:
        try:
            return await self._run(ctx)
        except Exception as exc:  # noqa: BLE001
            return error_signal(NAME, TITLE, exc, WEIGHT)

    async def _run(self, ctx: AnalysisContext) -> Signal:
        settings = ctx.settings
        if not settings or not settings.google_factcheck_api_key:
            return skipped_signal(
                NAME,
                TITLE,
                "No Google Fact Check API key configured (free at console.cloud.google.com — "
                "set VERIFACT_GOOGLE_FACTCHECK_API_KEY).",
                WEIGHT,
            )

        queries = [c.text[:200] for c in ctx.claims[:4] if c.checkworthy]
        if not queries and ctx.meta.title:
            queries = [ctx.meta.title[:200]]
        if not queries:
            return skipped_signal(NAME, TITLE, "No claims available to search.", WEIGHT)

        findings: list[Finding] = []
        matches = neg = pos = 0
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            for q in queries:
                resp = await client.get(
                    API,
                    params={
                        "key": settings.google_factcheck_api_key,
                        "query": q,
                        "pageSize": 3,
                        "languageCode": "en",
                    },
                )
                if resp.status_code != 200:
                    continue
                for item in resp.json().get("claims", []):
                    for review in item.get("claimReview", []):
                        matches += 1
                        rating = review.get("textualRating", "unrated")
                        pol = rating_polarity(rating)
                        neg += pol < 0
                        pos += pol > 0
                        findings.append(
                            Finding(
                                label=f"{review.get('publisher', {}).get('name', 'Fact-checker')}: "
                                f"“{rating}”",
                                detail=item.get("text", q)[:220],
                                impact="negative" if pol < 0 else ("positive" if pol > 0 else "neutral"),
                                evidence_url=review.get("url"),
                            )
                        )

        if matches == 0:
            return Signal(
                name=NAME,
                title=TITLE,
                status=SignalStatus.OK,
                score=None,  # absence of a fact-check is not evidence either way
                weight=0,
                confidence=0.3,
                summary="No existing fact-checks matched these claims (not evidence either way).",
            )

        if neg > pos:
            score, summary = 15.0, (
                f"{neg} of {matches} matched fact-check(s) rate related claims FALSE/misleading."
            )
        elif pos > neg:
            score, summary = 85.0, (
                f"{pos} matched fact-check(s) support related claims as accurate."
            )
        else:
            score, summary = 50.0, f"{matches} related fact-check(s) found with mixed ratings."

        return Signal(
            name=NAME,
            title=TITLE,
            status=SignalStatus.OK,
            score=score,
            weight=WEIGHT,
            confidence=0.8,
            summary=summary,
            findings=findings[:10],
            raw={"matches": matches, "negative": neg, "positive": pos},
        )
