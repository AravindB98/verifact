from verifact.models import CredibilityReport, Signal, SignalStatus, Verdict
from verifact.scoring import aggregate, finalize


def sig(name="s", score=80.0, weight=1.0, confidence=0.8, status=SignalStatus.OK):
    return Signal(
        name=name, title=name, status=status, score=score, weight=weight, confidence=confidence
    )


def test_insufficient_with_few_signals():
    score, verdict, conf = aggregate([sig()])
    assert score is None
    assert verdict == Verdict.INSUFFICIENT


def test_high_credibility_band():
    score, verdict, _ = aggregate([sig(score=90), sig(name="b", score=85), sig(name="c", score=80)])
    assert verdict == Verdict.HIGH
    assert score >= 75


def test_very_low_band():
    score, verdict, _ = aggregate([sig(score=10), sig(name="b", score=15)])
    assert verdict == Verdict.VERY_LOW


def test_weighting_pulls_score():
    heavy_bad = sig(name="bad", score=0, weight=5, confidence=1.0)
    light_good = sig(name="good", score=100, weight=0.5, confidence=0.5)
    score, verdict, _ = aggregate([heavy_bad, light_good])
    assert score < 30


def test_known_bad_source_caps_score():
    src = sig(name="source_reputation", score=8, weight=2.5, confidence=0.85)
    style = sig(name="content_signals", score=95, weight=1.5, confidence=0.9)
    other = sig(name="x", score=90, weight=2.0, confidence=0.9)
    score, verdict, _ = aggregate([src, style, other])
    assert score <= 30
    assert verdict in (Verdict.VERY_LOW, Verdict.LOW)


def test_skipped_and_none_scores_excluded():
    signals = [
        sig(),
        sig(name="skipped", status=SignalStatus.SKIPPED),
        sig(name="info", score=None),
        sig(name="b", score=70),
    ]
    score, verdict, _ = aggregate(signals)
    assert score is not None


def test_finalize_populates_report():
    report = CredibilityReport(signals=[sig(), sig(name="b", score=60)])
    report = finalize(report)
    assert report.score is not None
    assert report.verdict_label
    assert report.summary
    assert report.analyzers_run == 2
