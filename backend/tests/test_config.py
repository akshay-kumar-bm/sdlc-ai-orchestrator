import json

from app.core.config import Settings


def test_settings_parses_mcp_servers(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    monkeypatch.setenv("MCP_SERVERS", json.dumps({
        "github": {
            "transport": "streamable_http",
            "url": "https://api.example/mcp",
            "headers": {"Authorization": "Bearer x"},
        }
    }))
    s = Settings()
    assert s.LLM_PROVIDER == "anthropic"
    assert s.MCP_SERVERS["github"]["transport"] == "streamable_http"
