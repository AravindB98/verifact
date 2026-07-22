"""Content acquisition: fetch a URL and extract the main article."""

from __future__ import annotations

import httpx
import tldextract
import trafilatura

from .config import get_settings
from .models import ContentMeta


class FetchError(Exception):
    pass


def domain_of(url: str) -> str:
    ext = tldextract.extract(url)
    return ".".join(p for p in (ext.domain, ext.suffix) if p)


async def fetch_url(url: str) -> tuple[str, ContentMeta]:
    """Fetch a URL, extract main text + metadata.

    Returns (main_text, meta). Raises FetchError on hard failures.
    """
    settings = get_settings()
    headers = {"User-Agent": settings.user_agent, "Accept-Language": "en;q=0.9,*;q=0.5"}
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=settings.http_timeout, headers=headers
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
            final_url = str(resp.url)
    except httpx.HTTPError as exc:  # noqa: BLE001 - single boundary
        raise FetchError(f"Could not fetch {url}: {exc}") from exc

    meta = ContentMeta(url=final_url, domain=domain_of(final_url))

    extracted = trafilatura.extract(
        html,
        url=final_url,
        include_comments=False,
        favor_precision=True,
        output_format="txt",
    )
    md = trafilatura.extract_metadata(html, default_url=final_url)
    if md:
        meta.title = md.title or None
        meta.author = md.author or None
        meta.published = md.date or None
        meta.language = getattr(md, "language", None)

    text = (extracted or "").strip()
    meta.word_count = len(text.split())
    meta.excerpt = text[:400]
    if not text:
        raise FetchError(
            f"Fetched {url} but could not extract readable article text "
            "(the page may be JavaScript-only, paywalled, or not an article)."
        )
    return text, meta


def meta_for_text(text: str) -> ContentMeta:
    text = text.strip()
    return ContentMeta(word_count=len(text.split()), excerpt=text[:400])
