import pytest

from verifact.analyzers.base import AnalysisContext
from verifact.analyzers.content_signals import ContentSignalsAnalyzer
from verifact.models import ContentMeta, SignalStatus

CLICKBAIT = (
    "SHOCKING TRUTH they don't want you to know!!! Doctors hate this miracle cure. "
    "WAKE UP PEOPLE!!! Share before it's deleted!!! The mainstream media won't tell you "
    "the real truth about this BANNED video. 100% proof the elites don't want you to see!!! "
) * 3

PROFESSIONAL = (
    'The finance ministry said on Tuesday that inflation eased to 4.1 percent in June, '
    'according to data released by the national statistics office. "We expect the trend '
    'to continue," a spokesperson said in a statement. Economists at three banks told '
    'reporters the figures matched forecasts. The central bank confirmed it would review '
    'rates in August. Officials reported that food prices declined for a second month, '
    'and analysts said the data suggested a stable outlook for households this year.'
)


@pytest.mark.asyncio
async def test_clickbait_scores_low():
    ctx = AnalysisContext(input_type="text", text=CLICKBAIT, meta=ContentMeta())
    s = await ContentSignalsAnalyzer().run(ctx)
    assert s.status == SignalStatus.OK
    assert s.score is not None and s.score < 40
    assert any(f.impact == "negative" for f in s.findings)


@pytest.mark.asyncio
async def test_professional_scores_high():
    ctx = AnalysisContext(input_type="text", text=PROFESSIONAL, meta=ContentMeta())
    s = await ContentSignalsAnalyzer().run(ctx)
    assert s.score is not None and s.score >= 65


@pytest.mark.asyncio
async def test_clickbait_lower_than_professional():
    bad = await ContentSignalsAnalyzer().run(
        AnalysisContext(input_type="text", text=CLICKBAIT, meta=ContentMeta())
    )
    good = await ContentSignalsAnalyzer().run(
        AnalysisContext(input_type="text", text=PROFESSIONAL, meta=ContentMeta())
    )
    assert bad.score < good.score
