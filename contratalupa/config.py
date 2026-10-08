"""Application configuration, loaded from environment variables (prefix ``CL_``)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CL_", env_file=".env", extra="ignore")

    environment: str = "local"

    # Provider cascade for the LLM, tried in order. Each reads its own API key
    # from the environment; a provider with no key fails at call time and the
    # cascade falls back to the next. When all fail, the analyser uses its
    # offline keyword heuristics, so the service always returns a result.
    llm_spec: str = "anthropic,openai,gemini,deepseek,ollama"
    llm_max_tokens: int = 400


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
