from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.core.llm_client import get_llm


def test_get_llm_anthropic(monkeypatch):
    monkeypatch.setattr(
        "app.core.llm_client.get_settings", lambda: _fake("anthropic", "claude-sonnet-4-6")
    )
    assert isinstance(get_llm(), ChatAnthropic)


def test_get_llm_openai_with_override(monkeypatch):
    monkeypatch.setattr("app.core.llm_client.get_settings", lambda: _fake("openai", "gpt-4o"))
    llm = get_llm(model_override="gpt-4o-mini")
    assert isinstance(llm, ChatOpenAI)


class _fake:
    def __init__(self, p, m):
        self.LLM_PROVIDER, self.LLM_MODEL = p, m
        self.ANTHROPIC_API_KEY = "x"
        self.OPENAI_API_KEY = "x"
