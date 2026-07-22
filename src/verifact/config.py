"""Configuration — every external key is OPTIONAL.

VeriFact is designed to degrade gracefully: with zero API keys it still runs
source-reputation, content-signal, heuristic claim extraction, metadata and
fact-check-database analyzers. Adding keys unlocks deeper analysis:

- ``VERIFACT_ANTHROPIC_API_KEY`` / ``VERIFACT_OPENAI_API_KEY`` → LLM claim
  extraction + per-claim reasoning.
- ``VERIFACT_GOOGLE_FACTCHECK_API_KEY`` → Google Fact Check Tools (ClaimReview)
  lookup. Free key from Google Cloud Console.
- ``VERIFACT_BRAVE_API_KEY`` or ``VERIFACT_TAVILY_API_KEY`` → live web
  corroboration search.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VERIFACT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM (optional) ---
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # --- Fact-check & search (optional) ---
    google_factcheck_api_key: str | None = None
    brave_api_key: str | None = None
    tavily_api_key: str | None = None

    # --- Behaviour ---
    http_timeout: float = 15.0
    user_agent: str = (
        "Mozilla/5.0 (compatible; VeriFactBot/0.1; +https://github.com/AravindB98/verifact)"
    )
    max_claims: int = 8
    cache_dir: str | None = None

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "*"

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key)

    @property
    def has_search(self) -> bool:
        return bool(self.brave_api_key or self.tavily_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
