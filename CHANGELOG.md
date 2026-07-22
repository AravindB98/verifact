# Changelog

All notable changes to VeriFact are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-07-22

### Added
- **Social-post analysis**: paste an X/Twitter status link and VeriFact
  extracts the post via public embed-grade endpoints (FixTweet, X
  syndication) — no login, no scraping. Instagram/Facebook/LinkedIn links
  use OpenGraph link-preview metadata where public, flagged as *partial
  extraction*. WhatsApp links get a clear explanation (forwards have no
  public URLs — paste the text instead).
- New `social_context` informational signal (platform, author, followers,
  partial-extraction flag).
- Fairer scoring for social posts: the host platform (x.com, etc.) is
  down-weighted in source reputation — the poster, not the platform, is
  the source.
- **Live demo website** (GitHub Pages, `site/` + `scripts/build_demo.py`):
  an entirely in-browser subset of the engine — source reputation, RDAP
  domain age, X-post extraction, style & claim heuristics, GDELT
  corroboration — with honest labeling of what needs the full engine.

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
