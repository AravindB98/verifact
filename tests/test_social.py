import pytest

from verifact.social import detect_platform, parse_og_meta


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://x.com/jack/status/20", "x"),
        ("https://twitter.com/jack/status/20", "x"),
        ("https://mobile.twitter.com/jack/statuses/20?s=1", "x"),
        ("https://www.instagram.com/p/AbC12_xyz/", "instagram"),
        ("https://www.instagram.com/reel/AbC12/", "instagram"),
        ("https://www.linkedin.com/posts/someone_activity-12345", "linkedin"),
        ("https://www.facebook.com/user/posts/123456", "facebook"),
        ("https://fb.watch/abcdef/", "facebook"),
        ("https://chat.whatsapp.com/InviteCode123", "whatsapp"),
        ("https://wa.me/15551234567", "whatsapp"),
        ("https://www.bbc.com/news/article-123", None),
        ("https://example.com/x.com/status/1", None),
    ],
)
def test_detect_platform(url, platform):
    assert detect_platform(url) == platform


def test_parse_og_meta_both_attribute_orders():
    html = """
    <html><head>
      <meta property="og:title" content="Big claim about the economy" />
      <meta content="Full post text with 42 percent statistics." property="og:description"/>
      <meta name="twitter:site" content="@example">
    </head></html>
    """
    og = parse_og_meta(html)
    assert og["og:title"] == "Big claim about the economy"
    assert "42 percent" in og["og:description"]
    assert og["twitter:site"] == "@example"


def test_parse_og_meta_unescapes_entities():
    html = '<meta property="og:title" content="Cats &amp; dogs &quot;together&quot;" />'
    og = parse_og_meta(html)
    assert og["og:title"] == 'Cats & dogs "together"'


async def test_whatsapp_raises_helpful_error():
    from verifact.extract import FetchError
    from verifact.social import fetch_social

    with pytest.raises(FetchError, match="[Pp]aste the forward"):
        await fetch_social("https://chat.whatsapp.com/Kx1InviteCode")


async def test_social_platform_neutralized_in_source_reputation():
    from verifact.analyzers.base import AnalysisContext
    from verifact.analyzers.source_reputation import SourceReputationAnalyzer
    from verifact.models import ContentMeta

    ctx = AnalysisContext(
        input_type="social",
        text="some post",
        meta=ContentMeta(url="https://x.com/a/status/1", domain="x.com"),
    )
    s = await SourceReputationAnalyzer().run(ctx)
    assert s.score == 50.0
    assert s.confidence <= 0.4
    assert "poster" in s.summary
