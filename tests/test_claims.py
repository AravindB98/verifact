from verifact.analyzers.claims import heuristic_claims

ARTICLE = (
    "The World Health Organization announced on Monday that measles cases rose 42 percent "
    "worldwide in 2025. Health Minister Anna Kovacs said vaccination coverage fell below "
    "80 percent in twelve countries. This is a beautiful time of year. What could go wrong? "
    "Researchers at Oxford University found that outbreak clusters correlated with regions "
    "where coverage dropped under 75 percent since 2021."
)


def test_extracts_claimlike_sentences():
    claims = heuristic_claims(ARTICLE, max_claims=5)
    assert 1 <= len(claims) <= 5
    joined = " ".join(c.text for c in claims)
    assert "42 percent" in joined or "80 percent" in joined


def test_skips_vibes_and_questions():
    claims = heuristic_claims(ARTICLE, max_claims=5)
    for c in claims:
        assert "beautiful time" not in c.text
        assert not c.text.endswith("?")


def test_respects_max():
    claims = heuristic_claims(ARTICLE * 5, max_claims=3)
    assert len(claims) <= 3


def test_short_text_yields_nothing():
    assert heuristic_claims("Hello world.", max_claims=5) == []
