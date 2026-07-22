"""Social-post extraction: turn platform share links into analyzable text.

Platforms are hostile to scraping, so this module uses only *public,
embed-grade* endpoints and metadata — no logins, no headless browsers:

- **X / Twitter**: the FixTweet public API (api.fxtwitter.com) first, then
  X's own embed syndication endpoint (cdn.syndication.twimg.com) — the same
  data that powers embedded tweets on any website.
- **Instagram / Facebook / LinkedIn**: OpenGraph metadata (``og:title``,
  ``og:description``) that platforms publish for link previews. This often
  contains the caption/post text, but is *partial* by design — reports are
  flagged accordingly so users know to paste the full text for a deep check.
- **WhatsApp**: forwards have no public URLs (``chat.whatsapp.com`` links are
  group invites). Callers get a clear error telling them to paste the text.

Extraction results feed the normal pipeline; ``ContentMeta`` isn't enough to
carry partiality, so ``SocialPost.partial`` flows into the report via the
claims/extraction notes.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from dataclasses import dataclass, field

import httpx

from .config import get_settings
from .extract import FetchError, domain_of
from .models import ContentMeta

_X_STATUS = re.compile(
    r"https?://(?:www\.|mobile\.)?(?:x\.com|twitter\.com)/(?:\w+|i/web)/status(?:es)?/(\d+)",
    re.IGNORECASE,
)
_INSTAGRAM = re.compile(r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[\w-]+", re.IGNORECASE)
_FACEBOOK = re.compile(r"https?://(?:www\.|m\.|mbasic\.)?facebook\.com/\S+|https?://fb\.watch/\S+", re.IGNORECASE)
_LINKEDIN = re.compile(r"https?://(?:www\.)?linkedin\.com/(?:posts|pulse|feed/update)/\S+", re.IGNORECASE)
_WHATSAPP = re.compile(r"https?://(?:chat\.whatsapp\.com|wa\.me|api\.whatsapp\.com)/\S*", re.IGNORECASE)

_OG_META = re.compile(
    r'<meta[^>]+(?:property|name)=["\']((?:og|twitter):[\w:.]+)["\'][^>]+content=["\']([^"\']*)["\']'
    r'|<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']((?:og|twitter):[\w:.]+)["\']',
    re.IGNORECASE,
)

FXTWITTER_API = "https://api.fxtwitter.com/status/{id}"
SYNDICATION_API = "https://cdn.syndication.twimg.com/tweet-result"


@dataclass
class SocialPost:
    platform: str
    text: str
    author: str | None = None
    published: str | None = None
    url: str = ""
    partial: bool = False  # og:-metadata extraction — may be truncated
    extras: dict = field(default_factory=dict)


def detect_platform(url: str) -> str | None:
    """Return platform key for a URL, or None if it's not a social link."""
    if _X_STATUS.search(url):
        return "x"
    if _INSTAGRAM.search(url):
        return "instagram"
    if _LINKEDIN.search(url):
        return "linkedin"
    if _FACEBOOK.search(url):
        return "facebook"
    if _WHATSAPP.search(url):
        return "whatsapp"
    return None


def parse_og_meta(html: str) -> dict[str, str]:
    """Extract og:/twitter: meta tags from raw HTML."""
    out: dict[str, str] = {}
    for m in _OG_META.finditer(html):
        key = m.group(1) or m.group(4)
        val = m.group(2) if m.group(1) else m.group(3)
        if key and val and key.lower() not in out:
            out[key.lower()] = htmllib.unescape(val)
    return out


async def _fetch_x(url: str, client: httpx.AsyncClient) -> SocialPost:
    tweet_id = _X_STATUS.search(url).group(1)  # type: ignore[union-attr]
    # 1) FixTweet — clean JSON, includes author metadata.
    try:
        resp = await client.get(FXTWITTER_API.format(id=tweet_id))
        if resp.status_code == 200:
            tw = resp.json().get("tweet") or {}
            if tw.get("text"):
                author = tw.get("author") or {}
                return SocialPost(
                    platform="x",
                    text=tw["text"],
                    author=author.get("name") or author.get("screen_name"),
                    published=tw.get("created_at"),
                    url=tw.get("url", url),
                    extras={
                        "likes": tw.get("likes"),
                        "retweets": tw.get("retweets"),
                        "author_followers": (author.get("followers")),
                    },
                )
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        pass
    # 2) X's own embed syndication endpoint.
    try:
        resp = await client.get(SYNDICATION_API, params={"id": tweet_id, "token": "1"})
        if resp.status_code == 200:
            data = resp.json()
            if data.get("text"):
                user = data.get("user") or {}
                return SocialPost(
                    platform="x",
                    text=data["text"],
                    author=user.get("name") or user.get("screen_name"),
                    published=data.get("created_at"),
                    url=url,
                )
    except (httpx.HTTPError, json.JSONDecodeError):
        pass
    raise FetchError(
        "Could not extract this X post (deleted, restricted, or endpoints unavailable). "
        "Paste the post text directly for a full analysis."
    )


async def _fetch_og(url: str, platform: str, client: httpx.AsyncClient) -> SocialPost:
    try:
        resp = await client.get(url)
        html = resp.text
    except httpx.HTTPError as exc:
        raise FetchError(f"Could not fetch {platform} link: {exc}") from exc

    og = parse_og_meta(html)
    title = og.get("og:title", "")
    desc = og.get("og:description", "")
    text = "\n".join(t for t in (title, desc) if t).strip()
    if len(text.split()) < 4:
        raise FetchError(
            f"{platform.capitalize()} returned no readable post content (login wall / private "
            "account). Paste the post text directly for a full analysis."
        )
    return SocialPost(
        platform=platform,
        text=text,
        author=og.get("og:title") if platform == "linkedin" else None,
        url=og.get("og:url", url),
        partial=True,
    )


async def fetch_social(url: str) -> tuple[str, ContentMeta, SocialPost]:
    """Extract a social post. Returns (text, meta, post). Raises FetchError."""
    platform = detect_platform(url)
    if platform is None:
        raise FetchError(f"Not a recognized social-media post URL: {url}")
    if platform == "whatsapp":
        raise FetchError(
            "WhatsApp forwards don't have public URLs (chat.whatsapp.com links are group "
            "invites, not messages). Paste the forward's text directly — text analysis is "
            "VeriFact's best-supported mode for forwards."
        )

    settings = get_settings()
    headers = {"User-Agent": settings.user_agent}
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=settings.http_timeout, headers=headers
    ) as client:
        if platform == "x":
            post = await _fetch_x(url, client)
        else:
            post = await _fetch_og(url, platform, client)

    meta = ContentMeta(
        url=url,
        domain=domain_of(url),
        title=(post.text.splitlines()[0][:120] if post.text else None),
        author=post.author,
        published=post.published,
        word_count=len(post.text.split()),
        excerpt=post.text[:400],
    )
    return post.text, meta, post
