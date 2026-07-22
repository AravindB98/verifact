# Changelog

All notable changes to VeriFact are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-07-22

### Added
- Core analysis pipeline with six analyzers: source reputation, writing-style
  signals, claim extraction (LLM + heuristic), fact-check database lookup
  (Google Fact Check Tools), independent corroboration (Brave/Tavily/GDELT),
  and media provenance (C2PA/EXIF/reverse-image pivots).
- Weighted, confidence-modulated scoring with honest
  `insufficient_evidence` verdict.
- `verifact` CLI (rich terminal reports, `--json` output, `serve` command).
- FastAPI REST API (`/api/v1/analyze`, `/api/v1/analyze/image`,
  `/api/v1/health`) with bundled single-file web UI.
- Chrome extension (Manifest V3) for one-click page verification.
- Docker image + docker-compose, GitHub Actions CI (lint, tests on
  3.10–3.12, Docker smoke test).
- Curated source-reputation dataset with citation-required contribution
  policy.
