from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def get_llm(model_override: str | None = None):
    s = get_settings()
    model = model_override or s.LLM_MODEL
    if s.LLM_PROVIDER == "anthropic":
        return ChatAnthropic(model=model, api_key=s.ANTHROPIC_API_KEY)
    return ChatOpenAI(model=model, api_key=s.OPENAI_API_KEY)
