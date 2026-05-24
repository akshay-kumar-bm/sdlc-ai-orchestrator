import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    LLM_PROVIDER: Literal["anthropic", "openai"] = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    WEBHOOK_SECRET: str = "change-me"

    # Option 1: inline JSON string
    MCP_SERVERS: dict[str, dict[str, Any]] = {}
    # Option 2: path to a JSON file (takes precedence over MCP_SERVERS if set)
    MCP_SERVERS_FILE: str | None = None

    @field_validator("MCP_SERVERS", mode="before")
    @classmethod
    def _parse_json(cls, v: Any) -> Any:
        return json.loads(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def _load_mcp_file(self) -> "Settings":
        if self.MCP_SERVERS_FILE and self.MCP_SERVERS_FILE.strip():
            path = Path(self.MCP_SERVERS_FILE)
            self.MCP_SERVERS = json.loads(path.read_text())
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
