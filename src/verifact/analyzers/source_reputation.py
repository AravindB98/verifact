"""Source reputation: who published this, and what do we know about them?

Signals used (all zero-key):
- Curated category lists (wire services, public broadcasters, fact-checkers,
  known low-credibility sites, satire, state-controlled media, UGC platforms).
- Domain age via RDAP (rdap.org bootstrap) — newly registered "news" domains
  are a classic disinformation tell.
- TLD heuristics and lookalike-domain detection (e.g. cnn-news24.co).
"""

from __future__ import annotations

import difflib
import json
import re
from datetime import datetime, timezone
from importlib import resources

import httpx

from ..models import Finding, Signal, SignalStatus
from .base import AnalysisContext, error_signal, skipped_signal

NAME = "source_reputation"
TITLE = "Source reputation"
WEIGHT = 2.5

CATEGORY_PRIORS: dict[str, tuple[float, str]] = {
    "wire_service": (92, "International wire service with editorial standards"),
    "fact_checker": (90, "Dedicated fact-checking organization (IFCN-style)"),
    "public_broadcaster": (88, "Public-service broadcaster"),
    "scientific": (88, "Scientific/peer-review publisher or index"),
    "intergovernmental": (85, "Government / intergovernmental body"),
    "established_news": (80, "Established news organization with corrections policy"),
    "user_generated": (40, "User-generated platform — credibility depends entirely on the poster"),
    "state_controlled_flagged": (
        20,
        "State-controlled outlet repeatedly flagged by independent media-credibility researchers",
    ),
    "low_credibility": (
        8,
        "Rated low-credibility by independent media-credibility researchers "
        "(repeated failed fact checks)",
    ),
    "satire": (15, "Satire site — content is intentionally fictional"),
}

_SUSPICIOUS_TLDS = {"xyz", "top", "click", "buzz", "live", "site", "online", "icu", "cfd", "sbs"}


def _load_lists() -> dict[str, list[str]]:
    with resources.files("verifact.data").joinpath("source_reputation.json").open() as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def categorize(domain: str, lists: dict[str, list[str]]) -> str | None:
    for category, domains in lists.items():
        if domain in domains:
            return category
    return None


def lookalike_of(domain: str, lists: dict[str, list[str]]) -> str | None:
    """Detect typosquats of reputable domains, e.g. 'reuters-news.co'."""
    reputable = [
        d
        for cat in ("wire_service", "established_news", "public_broadcaster")
        for d in lists.get(cat, [])
    ]
    base = domain.split(".")[0]
    for real in reputable:
        real_base = real.split(".")[0]
        if base == real_base and domain != real:
            return real  # same name, different TLD
        if real_base in base and base != real_base and len(real_base) >= 3:
            return real  # embedded brand, e.g. cnn-news24
        if (
            len(real_base) > 4
            and difflib.SequenceMatcher(None, base, real_base).ratio() > 0.86
            and base != real_base
        ):
            return real  # close typo
    return None


async def domain_age_days(domain: str, timeout: float) -> int | None:
    """Registration age via RDAP; returns None when unavailable."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(f"https://rdap.org/domain/{domain}")
            if resp.status_code != 200:
                return None
            events = resp.json().get("events", [])
        for ev in events:
            if ev.get("eventAction") == "registration":
                raw = ev.get("eventDate", "")
                raw = re.sub(r"Z$", "+00:00", raw)
                dt = datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - dt).days
    except Exception:  # noqa: BLE001 — analyzer must not raise
        return None
    return None


class SourceReputationAnalyzer:
    name = NAME
    title = TITLE

    async def run(self, ctx: AnalysisContext) -> Signal:
        try:
            return await self._run(ctx)
        except Exception as exc:  # noqa: BLE001
            return error_signal(NAME, TITLE, exc, WEIGHT)

    async def _run(self, ctx: AnalysisContext) -> Signal:
        domain = (ctx.meta.domain or "").lower()
        if not domain:
            return skipped_signal(
                NAME, TITLE, "No source domain (raw text input) — cannot assess publisher.", WEIGHT
            )

        lists = _load_lists()
        findings: list[Finding] = []
        score = 50.0  # unknown-domain prior
        confidence = 0.4

        category = categorize(domain, lists)
        if category == "user_generated" and ctx.input_type == "social":
            # For an individual post, the *platform* is not the publisher —
            # don't let "it's on X/Instagram" dominate the verdict either way.
            return Signal(
                name=NAME,
                title=TITLE,
                status=SignalStatus.OK,
                score=50.0,
                weight=WEIGHT * 0.4,
                confidence=0.3,
                summary=f"{domain} is a user-generated platform — the poster, not the platform, "
                "is the source. Judge by the claim and corroboration signals.",
                findings=[
                    Finding(
                        label="User-generated platform",
                        detail=f"{domain}: anyone can post; platform reputation carries little "
                        "signal for an individual post.",
                        impact="informational",
                    )
                ],
                raw={"domain": domain, "category": category, "age_days": None},
            )
        if category:
            prior, label = CATEGORY_PRIORS[category]
            score = prior
            confidence = 0.85
            impact = "positive" if prior >= 70 else ("negative" if prior <= 40 else "neutral")
            findings.append(Finding(label=f"Known source: {label}", detail=domain, impact=impact))
        else:
            findings.append(
                Finding(
                    label="Domain not in curated lists",
                    detail=f"{domain} has no prior reputation record in VeriFact's dataset.",
                    impact="informational",
                )
            )
            fake = lookalike_of(domain, lists)
            if fake:
                score = min(score, 15)
                confidence = 0.8
                findings.append(
                    Finding(
                        label="Possible lookalike domain",
                        detail=f"'{domain}' resembles reputable outlet '{fake}' — a common "
                        "impersonation tactic.",
                        impact="negative",
                    )
                )
            tld = domain.rsplit(".", 1)[-1]
            if tld in _SUSPICIOUS_TLDS:
                score -= 10
                findings.append(
                    Finding(
                        label=f"Cheap/abuse-prone TLD (.{tld})",
                        detail="Frequently used by disposable disinformation sites.",
                        impact="negative",
                    )
                )

        settings = ctx.settings
        age = await domain_age_days(domain, settings.http_timeout if settings else 10.0)
        if age is not None:
            years = age / 365.25
            if age < 180 and not category:
                score -= 20
                confidence = max(confidence, 0.6)
                findings.append(
                    Finding(
                        label="Very new domain",
                        detail=f"Registered ~{age} days ago. Fresh domains publishing 'news' "
                        "are a classic disinformation pattern.",
                        impact="negative",
                    )
                )
            elif years >= 10:
                score += 5
                findings.append(
                    Finding(
                        label="Long-established domain",
                        detail=f"Registered ~{years:.0f} years ago.",
                        impact="positive",
                    )
                )
            else:
                findings.append(
                    Finding(
                        label="Domain age",
                        detail=f"Registered ~{years:.1f} years ago.",
                        impact="informational",
                    )
                )

        score = max(0.0, min(100.0, score))
        if category == "satire":
            summary = f"{domain} is a known satire site — treat content as fiction."
        elif category:
            summary = f"{domain}: {CATEGORY_PRIORS[category][1].lower()}."
        else:
            summary = f"{domain} is not a recognized outlet; judge by corroboration, not brand."

        return Signal(
            name=NAME,
            title=TITLE,
            status=SignalStatus.OK,
            score=score,
            weight=WEIGHT,
            confidence=confidence,
            summary=summary,
            findings=findings,
            raw={"domain": domain, "category": category, "age_days": age},
        )
