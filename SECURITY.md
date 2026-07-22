# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.
Use GitHub's [private vulnerability reporting](https://github.com/AravindB98/verifact/security/advisories/new)
instead. You'll get an acknowledgement within 72 hours.

## Scope notes

- VeriFact fetches attacker-controlled web pages by design. SSRF hardening
  matters: if you find a way to make the fetcher hit internal networks,
  cloud metadata endpoints, or local files, that's a valid report.
- API keys live only in environment variables / `.env` (gitignored). Any code
  path that could leak keys into reports, logs, or error messages is a valid
  report.
- Prompt-injection against the optional LLM analyzers (e.g. a malicious
  article manipulating its own credibility assessment) is a known, interesting
  attack surface — reports and mitigations are very welcome.
