# VeriFact architecture

```
                       ┌──────────────────────────────────────────┐
  URL / text / image → │              PIPELINE                    │
                       │                                          │
                       │  1. extract.py    fetch + main-article   │
                       │                   extraction (trafilatura)│
                       │  2. claims.py     claim extraction        │
                       │                   (LLM or heuristic)      │
                       │  3. analyzers     run concurrently:       │
                       │     • source_reputation  (weight 2.5)     │
                       │     • factcheck_db       (weight 2.0)     │
                       │     • corroboration      (weight 2.0)     │
                       │     • content_signals    (weight 1.5)     │
                       │     • media_provenance   (weight 1.5)     │
                       │     • claims             (weight 1.0)     │
                       │  4. scoring.py    weighted, confidence-   │
                       │                   modulated aggregation   │
                       └───────────────┬──────────────────────────┘
                                       ▼
                            CredibilityReport (JSON)
                                       ▼
                 ┌─────────────┬───────────────┬──────────────┐
                 │   CLI       │  FastAPI      │  Chrome ext.  │
                 │ (rich TTY)  │  + web UI     │  (popup)      │
                 └─────────────┴───────────────┴──────────────┘
```

## Design invariants

1. **Analyzers never raise.** Each catches its own errors and reports
   `status: error`. One flaky network call must not sink a report.
2. **Zero-key first.** Source reputation, content signals, heuristic claims,
   GDELT corroboration and media metadata all run with no API keys.
   Key-gated analyzers report `status: skipped` with instructions —
   they are never silently faked.
3. **Score ∈ [0,100] or None.** `None` = informational-only signal
   (excluded from aggregation). The aggregate needs ≥2 scoring signals,
   otherwise the verdict is `insufficient_evidence`.
4. **Confidence modulates weight.** Aggregate = Σ(score·weight·confidence) /
   Σ(weight·confidence). A guard caps the final score at 30 when a
   high-confidence source-reputation or fact-check signal is ≤15 —
   good grammar must not rescue a known disinformation outlet.
5. **Evidence, not oracle.** Every score ships with findings + URLs so a
   human can check the work. The disclaimer is part of the API contract.

## Adding an analyzer

```python
# src/verifact/analyzers/my_signal.py
from ..models import Signal, SignalStatus
from .base import AnalysisContext, error_signal

NAME, TITLE, WEIGHT = "my_signal", "My signal", 1.0

class MySignalAnalyzer:
    name, title = NAME, TITLE

    async def run(self, ctx: AnalysisContext) -> Signal:
        try:
            ...
            return Signal(name=NAME, title=TITLE, status=SignalStatus.OK,
                          score=42.0, weight=WEIGHT, confidence=0.6,
                          summary="…", findings=[...])
        except Exception as exc:
            return error_signal(NAME, TITLE, exc, WEIGHT)
```

Register it in `pipeline.py` (`stage2` list) and `analyzers/__init__.py`,
add offline tests, done.

## Threat model notes

- Fetcher hits attacker-controlled pages: keep SSRF in mind (see SECURITY.md).
- LLM analyzers read attacker-controlled text: prompt injection can attempt
  to inflate credibility. Mitigation: LLM output is parsed as strict JSON,
  contributes bounded score/weight, and never overrides the low-source guard.
- Source lists are a governance surface: changes require citations (see
  CONTRIBUTING.md).
