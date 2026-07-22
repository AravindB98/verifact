"""Cross-source corroboration: is anyone independent reporting the same thing?

Uses (in order of preference):
- Brave Search API (``VERIFACT_BRAVE_API_KEY``, generous free tier), or
- Tavily API (``VERIFACT_TAVILY_API_KEY``), or
- GDELT DOC 2.0 API (zero-key, news-only, best-effort).

The question is never "does the internet agree?" but "do *independent,
reputable* outlets carry this story?" — so results from the same domain as
the input are excluded, and hits on known-reputable outlets weigh more.
"""

from __future__ import annotations

import json
from importlib import resources

import httpx

from ..extract import domain_of
from ..models import Finding, Signal, SignalStatus
from .base import AnalysisContext, error_signal, skipped_signal

NAME = "corroboration"
TITLE = "Independent corroboration"
WEIGHT = 2.0

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def _reputable_domains() -> set[str]:
    with resources.files("verifact.data").joinpath("source_reputation.json").open() as f:
        data = json.load(f)
    cats = ("wire_service", "public_broadcaster", "established_news", "fact_checker")
    return {d for c in cats for d in data.get(c, [])}


async def _brave(client: httpx.AsyncClient, key: str, query: str) -> list[dict]:
    resp = await client.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": key},
        params={"q": query, "count": 8},
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title", ""), "url": r.get("url", "")}
        for r in resp.json().get("web", {}).get("results", [])
    ]


async def _tavily(client: httpx.AsyncClient, key: str, query: str) -> list[dict]:
    resp = await client.post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": 8},
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title", ""), "url": r.get("url", "")}
        for r in resp.json().get("results", [])
    ]


async def _gdelt(client: httpx.AsyncClient, query: str) -> list[dict]:
    resp = await client.get(
        GDELT_API,
        params={"query": query, "mode": "artlist", "maxrecords": 10, "format": "json"},
    )
    resp.raise_for_status()
    try:
        articles = resp.json().get("articles", [])
    except ValueError:
        return []
    return [{"title": a.get("title", ""), "url": a.get("url", "")} for a in articles]


class CorroborationAnalyzer:
    name = NAME
    title = TITLE

    async def run(self, ctx: AnalysisContext) -> Signal:
        try:
            return await self._run(ctx)
        except Exception as exc:  # noqa: BLE001
            return error_signal(NAME, TITLE, exc, WEIGHT)

    async def _run(self, ctx: AnalysisContext) -> Signal:
        settings = ctx.settings
        query = None
        if ctx.claims:
            query = ctx.claims[0].text[:180]
        elif ctx.meta.title:
            query = ctx.meta.title[:180]
        if not query:
            return skipped_signal(NAME, TITLE, "Nothing searchable (no title or claims).", WEIGHT)

        own_domain = (ctx.meta.domain or "").lower()
        provider = "gdelt"
        results: list[dict] = []
        timeout = settings.http_timeout if settings else 15.0
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if settings and settings.brave_api_key:
                provider, results = "brave", await _brave(client, settings.brave_api_key, query)
            elif settings and settings.tavily_api_key:
                provider, results = "tavily", await _tavily(client, settings.tavily_api_key, query)
            else:
                try:
                    results = await _gdelt(client, f'"{query[:80]}"' if len(query) > 20 else query)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 429:
                        return skipped_signal(
                            NAME,
                            TITLE,
                            "GDELT free API is rate-limited right now — retry shortly, or set "
                            "VERIFACT_BRAVE_API_KEY / VERIFACT_TAVILY_API_KEY for reliable "
                            "corroboration search.",
                            WEIGHT,
                        )
                    raise

        independent = [r for r in results if r["url"] and domain_of(r["url"]).lower() != own_domain]
        reputable_set = _reputable_domains()
        reputable_hits = [r for r in independent if domain_of(r["url"]).lower() in reputable_set]

        findings = [
            Finding(
                label=domain_of(r["url"]),
                detail=r["title"][:180],
                impact="positive" if domain_of(r["url"]).lower() in reputable_set else "neutral",
                evidence_url=r["url"],
            )
            for r in independent[:8]
        ]

        if not independent:
            return Signal(
                name=NAME,
                title=TITLE,
                status=SignalStatus.OK,
                score=30.0,
                weight=WEIGHT * 0.6,  # soften: could be very fresh news
                confidence=0.45,
                summary=f"No independent coverage found via {provider} — either very fresh, "
                "very niche, or nobody else considers it news. Treat with caution.",
                findings=findings,
                raw={"provider": provider, "query": query},
            )

        if reputable_hits:
            score = min(95.0, 65 + 8 * len(reputable_hits))
            summary = (
                f"{len(reputable_hits)} reputable independent outlet(s) carry related coverage "
                f"({provider} search)."
            )
            confidence = 0.7
        else:
            score = 50.0
            summary = (
                f"{len(independent)} independent page(s) mention it, but none from "
                "recognized outlets — corroboration is weak."
            )
            confidence = 0.5

        return Signal(
            name=NAME,
            title=TITLE,
            status=SignalStatus.OK,
            score=score,
            weight=WEIGHT,
            confidence=confidence,
            summary=summary,
            findings=findings,
            raw={"provider": provider, "query": query, "hits": len(independent)},
        )
