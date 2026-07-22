<div align="center">

# 🛡️ VeriFact

### Verify before you trust.

**An open-source credibility engine for news, web content & social media —
provenance, claim verification, source reputation and manipulation signals,
with evidence you can check yourself.**

[![CI](https://github.com/AravindB98/verifact/actions/workflows/ci.yml/badge.svg)](https://github.com/AravindB98/verifact/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub stars](https://img.shields.io/github/stars/AravindB98/verifact?style=social)](https://github.com/AravindB98/verifact/stargazers)

⭐ **If VeriFact helps you (or someone you know who forwards *everything* on WhatsApp), please [star the repo](https://github.com/AravindB98/verifact/stargazers) and [fork it](https://github.com/AravindB98/verifact/fork) — stars and forks are how open-source tools against misinformation get discovered.** ⭐

</div>

---

## Why VeriFact?

Misinformation moves faster than fact-checkers ever can. Most of us have no
practical way to answer a simple question in the moment: **"Should I trust
this article / post / forward?"**

VeriFact answers it the only honest way software can — not with a magic
true/false oracle, but with **stacked, transparent evidence**:

| Signal | Question it answers | Works with zero keys? |
|---|---|---|
| 🏛️ **Source reputation** | Who published this? Wire service, satire site, known disinfo outlet, 3-week-old lookalike domain? | ✅ |
| ✍️ **Writing-style signals** | Does it *behave* like journalism — attribution, bylines, dates — or like viral bait (ALL CAPS, "share before deleted")? | ✅ |
| 🔍 **Claim extraction** | What are the actual falsifiable claims here? | ✅ (heuristic) · 🔑 LLM mode |
| 📚 **Fact-check databases** | Has Snopes / PolitiFact / AltNews / AFP already checked this? | 🔑 free Google key |
| 🌐 **Independent corroboration** | Is *anyone reputable and independent* reporting the same thing? | ✅ (GDELT) · 🔑 better with Brave/Tavily |
| 🖼️ **Media provenance** | Does the image carry C2PA Content Credentials? Editing traces? Where did it appear before? | ✅ |

Every report ends in an evidence list with links — **VeriFact shows its
work**, and refuses to score at all (`insufficient_evidence`) when the
signals aren't there. No truth oracle. No black box.

## ✨ Three ways to use it

**1. Web UI** — paste a link or a suspicious WhatsApp forward:

```bash
pip install git+https://github.com/AravindB98/verifact
verifact serve            # → open http://127.0.0.1:8000
```

**2. CLI** — for terminal people and scripts:

```bash
verifact analyze https://example-news.com/big-story
verifact analyze "Scientists CONFIRM this one weird trick cures everything!!!"
verifact analyze suspicious_photo.jpg --caption "flood in Chennai yesterday"
verifact analyze <url> --json      # full machine-readable report
```

**3. Chrome extension** — one-click check of the page you're reading:
load `extension/` via `chrome://extensions` → *Developer mode* → *Load
unpacked* (talks to your local `verifact serve`).

Or run everything in Docker:

```bash
docker compose up          # → http://127.0.0.1:8000
```

## 🖥️ What a report looks like

```
╭─────────────────────────── VeriFact v0.1.0 ───────────────────────────╮
│ 🚨 Very low credibility  22.4/100  (confidence 71%)                   │
│                                                                       │
│ 3 red flag(s). Strongest signal — source reputation:                  │
│ newsbreaking-24.xyz is not a recognized outlet; registered 41 days    │
│ ago; judge by corroboration, not brand.                               │
╰───────────────────────────────────────────────────────────────────────╯
 Signal                  Score  Details
 Source reputation          15  Very new domain, cheap TLD, no reputation record
 Writing-style signals      31  Sensational phrasing (4 hits), no attribution,
                                pressure to share
 Claim extraction           60  3 check-worthy claims extracted
 Independent corroboration  30  No independent coverage found
 Fact-check databases      skip No API key configured (free key available)
```

## ⚙️ Configuration (all optional)

VeriFact is **zero-key first**: it works out of the box. Keys unlock depth —
copy `.env.example` to `.env`:

| Variable | Unlocks | Cost |
|---|---|---|
| `VERIFACT_ANTHROPIC_API_KEY` *or* `VERIFACT_OPENAI_API_KEY` | LLM claim extraction & reasoning | paid |
| `VERIFACT_GOOGLE_FACTCHECK_API_KEY` | Global ClaimReview fact-check lookup | **free** |
| `VERIFACT_BRAVE_API_KEY` *or* `VERIFACT_TAVILY_API_KEY` | Live corroboration search | free tier |

Skipped analyzers are reported transparently — never silently faked.

## 🧠 How scoring works

Weighted, confidence-modulated average across all signals that produced a
score, with two honesty rules baked in:

1. **≥2 scoring signals required**, otherwise verdict = `insufficient_evidence`.
2. **Known-bad-source guard**: a high-confidence "this is a flagged disinfo
   outlet / fact-checked false" signal caps the total at 30 — good grammar
   can't rescue a known liar.

Read the full design in [`docs/architecture.md`](docs/architecture.md).

## 🗺️ Roadmap

- [ ] Social-post deep links (X/Twitter, Telegram, YouTube transcripts)
- [ ] AI-image detection ensemble + C2PA signing verification UI
- [ ] Multilingual sensational-term packs (Hindi, Tamil, Spanish, PT-BR…)
- [ ] Propagation analysis — who amplified this first?
- [ ] Browser extension on Chrome Web Store / Firefox Add-ons
- [ ] Claim-level corroboration matrix (per-claim search, not per-article)

Want one of these sooner? **[Fork the repo](https://github.com/AravindB98/verifact/fork)**, grab an issue, and send a PR — see [CONTRIBUTING.md](CONTRIBUTING.md).

## ⚖️ Honest limitations

- VeriFact estimates **credibility, not truth**. A scrappy blog can be right;
  a legacy outlet can be wrong.
- Breaking news often has no corroboration *yet* — VeriFact says
  "unverifiable right now", which is the correct answer, not a bug.
- AI-generated *text* is essentially undetectable today; we don't pretend
  otherwise.
- Source lists are curated and citation-gated, but inherently incomplete —
  PRs with evidence are the fix.

## 🤝 Contributing & Community

Contributions of every size are welcome — analyzers, source-list citations,
language packs, docs. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the
[good first issues](https://github.com/AravindB98/verifact/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

<div align="center">

**If you read this far — that's exactly the kind of person this project
needs. [⭐ Star](https://github.com/AravindB98/verifact/stargazers) ·
[🍴 Fork](https://github.com/AravindB98/verifact/fork) ·
[🐛 Report an issue](https://github.com/AravindB98/verifact/issues/new/choose)**

*Built with the conviction that the antidote to misinformation isn't
censorship — it's making verification effortless.*

</div>

## 📄 License

[Apache-2.0](LICENSE) © 2026 Aravind Balaji
