import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    LLM_PROVIDER: Literal["anthropic", "openai"] = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    WEBHOOK_SECRET: str = "change-me"

    # JSON map: { "<server>": { "transport": "...", "url": "...", "headers": {...} } }
    # or stdio: { "<server>": { "transport": "stdio", "command": "...", "args": [...] } }
    MCP_SERVERS: dict[str, dict[str, Any]] = {}

    @field_validator("MCP_SERVERS", mode="before")
    @classmethod
    def _parse_json(cls, v: Any) -> Any:
        return json.loads(v) if isinstance(v, str) else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
