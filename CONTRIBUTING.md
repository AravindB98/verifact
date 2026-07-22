# Contributing to VeriFact

First off — thank you! Fighting misinformation is a team sport, and every
contribution matters, from a typo fix to a new analyzer. If you find the
project useful, **please ⭐ star and 🍴 fork the repo** — it directly helps
more people discover it.

## Ways to contribute

- **Curated source lists** (`src/verifact/data/source_reputation.json`) —
  add domains *with citations* (IFCN signatory lists, academic datasets,
  published media-credibility research). PRs without evidence are declined.
- **New analyzers** — implement the `Analyzer` protocol in
  `src/verifact/analyzers/` (see `base.py`). Rules: never raise, degrade
  gracefully without API keys, return honest `confidence`.
- **Language support** — sensational-term lists and claim heuristics are
  English-first today. Hindi, Tamil, Spanish, Portuguese… all welcome.
- **Bug reports & docs** — use the issue templates.

## Dev setup

```bash
git clone https://github.com/AravindB98/verifact
cd verifact
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q          # run tests
ruff check src tests
verifact serve     # http://127.0.0.1:8000
```

## Pull request checklist

1. One logical change per PR.
2. `pytest` and `ruff check` pass.
3. New analyzers ship with tests that run **offline** (mock network calls).
4. Data-list changes cite sources in the PR description.

## Design principles (please read before big PRs)

1. **Evidence over verdicts** — VeriFact shows *why*, never just a number.
2. **Zero-key first** — the default experience must work with no API keys.
3. **Honest uncertainty** — when we don't know, we say `insufficient_evidence`.
4. **No truth oracle** — we estimate credibility signals; we do not declare
   absolute truth. Wording in code and docs must respect this line.

## Code of Conduct

Be excellent to each other — see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
