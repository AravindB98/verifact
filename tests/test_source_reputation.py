from verifact.analyzers.source_reputation import _load_lists, categorize, lookalike_of


def test_categorize_known_domains():
    lists = _load_lists()
    assert categorize("reuters.com", lists) == "wire_service"
    assert categorize("theonion.com", lists) == "satire"
    assert categorize("infowars.com", lists) == "low_credibility"
    assert categorize("x.com", lists) == "user_generated"
    assert categorize("some-random-blog.example", lists) is None


def test_lookalike_detection():
    lists = _load_lists()
    assert lookalike_of("cnn-news24.co", lists)  # embedded brand
    assert lookalike_of("reuters.co", lists)  # same name, different TLD
    assert lookalike_of("kitchenrecipes.com", lists) is None


def test_priors_are_sane():
    from verifact.analyzers.source_reputation import CATEGORY_PRIORS

    assert CATEGORY_PRIORS["wire_service"][0] > CATEGORY_PRIORS["user_generated"][0]
    assert CATEGORY_PRIORS["low_credibility"][0] < 20
